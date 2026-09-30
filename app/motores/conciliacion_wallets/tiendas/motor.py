"""Punto de entrada del motor para wallets de TIENDA (rol DROPSHIPPER o PROVEEDOR). Python puro.

    r = conciliar_wallet_tienda(ordenes_crudo, wallet_crudo, params, catalogo, tienda, periodo_inicio, periodo_fin,
                                tarifas_ff=None)

- `params`   = parametros_wallet_tienda.json
- `catalogo` = catalogo_conceptos_wallets.json
- `tienda`   = una entrada de params["tiendas"] (usuario_email, rol, empresa, ...)
- `tarifas_ff` = fulfillment.tarifas_por_bodega de parametros_wallet_wiilog.json (una sola fuente de verdad).
  Solo se usa con rol PROVEEDOR.
- `corte_ordenes` = fecha y hora de descarga del reporte de órdenes (opcional; por defecto, fin del día de FECHA DE REPORTE).

El núcleo guarda cargas, movimientos, resultados y hallazgos. Este módulo no sabe nada de base de datos.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .. import catalogo as cat
from ..wiilog import carga, movimientos
from ..wiilog import normalizar as n
from . import ordenes as ord_
from . import reglas

CONCEPTOS_DE_ORDEN = [
    "GANANCIA_DROPSHIPPER",
    "GANANCIA_PROVEEDOR",
    "CORRECCION_GUIA_DROPSHIPPER",
    "CORRECCION_GUIA_PROVEEDOR",
    "COBRO_NUEVA_ORDEN",
    "REEMBOLSO_CAMBIO_ESTATUS",
    "COBRO_DEVOLUCION",
    "COBRO_FLETE_INICIAL",
    "COBRO_FULFILLMENT",
    "REVERSO_COBRO_FF",
]


@dataclass
class ResultadoTienda:
    bloqueado: bool
    chequeos: list
    tienda: dict = field(default_factory=dict)
    movimientos: pd.DataFrame | None = None
    ganancia: pd.DataFrame | None = None
    sin_recaudo: pd.DataFrame | None = None
    devoluciones: pd.DataFrame | None = None
    fulfillment: pd.DataFrame | None = None
    fuera_del_reporte: pd.DataFrame | None = None
    resumen: dict = field(default_factory=dict)


def conciliar_wallet_tienda(
    ordenes_crudo, wallet_crudo, params, catalogo, tienda, periodo_inicio, periodo_fin, tarifas_ff=None, corte_ordenes=None
) -> ResultadoTienda:
    wallet = carga.leer_wallet(wallet_crudo, params)
    chequeos = movimientos.validar_integridad(wallet, periodo_inicio, periodo_fin)
    if any(c.estado == "BLOQUEADO" for c in chequeos):
        return ResultadoTienda(bloqueado=True, chequeos=chequeos, tienda=tienda)

    mov = cat.categorizar(wallet, catalogo, {**tienda, "wallets_propias": params.get("wallets_propias", []), "cuentas_destino_grupo": params.get("cuentas_destino_grupo", [])})
    ordenes = ord_.leer_ordenes_tienda(ordenes_crudo, params, tienda)
    corte_wallet = mov["fecha"].max()
    # Hora exacta de descarga del reporte si se conoce (va en el nombre del archivo); si no, fin del día del reporte.
    corte_ordenes = pd.Timestamp(corte_ordenes) if corte_ordenes is not None else ord_.fecha_reporte(ordenes_crudo, params)
    por_orden = reglas.movimientos_por_orden(mov)

    r = ResultadoTienda(bloqueado=False, chequeos=chequeos, tienda=tienda, movimientos=mov)
    r.ganancia = reglas.ganancia(ordenes, por_orden, tienda, params, corte_wallet, corte_ordenes)
    if tienda["rol"] == "DROPSHIPPER":
        r.sin_recaudo = reglas.orden_sin_recaudo(ordenes, por_orden, params)
        r.devoluciones = reglas.devolucion_con_recaudo(ordenes, por_orden, params, corte_wallet)
    else:
        r.fulfillment = reglas.fulfillment_proveedor(ordenes, por_orden, params, tarifas_ff or {}, corte_wallet, corte_ordenes)
    ids_reporte = ordenes_crudo[params["columnas_ordenes"]["orden_id"]].map(n.orden_id)
    r.fuera_del_reporte = reglas.fuera_del_reporte(mov, ordenes, CONCEPTOS_DE_ORDEN, ids_reporte)
    r.resumen = resumir(r, corte_wallet, corte_ordenes)
    return r


def _p(c) -> str:
    return str(n.pesos(int(c)))


def _por_estado(df: pd.DataFrame, col: str = "estado") -> dict:
    g = df.groupby(col).agg(ordenes=(col, "size"), en_juego_c=("monto_en_juego_c", "sum"))
    return {k: {"ordenes": int(v.ordenes), "monto_en_juego": _p(v.en_juego_c)} for k, v in g.iterrows()}


def resumir(r: ResultadoTienda, corte_wallet, corte_ordenes) -> dict:
    mov = r.movimientos
    flujo = mov.groupby(["ingreso_egreso", "concepto"]).agg(n=("mov_id", "size"), c=("monto_c", "sum"))
    out = {
        "tienda": r.tienda["usuario_email"],
        "rol": r.tienda["rol"],
        "corte_wallet": str(corte_wallet),
        "corte_reporte_ordenes": str(corte_ordenes),
        "movimientos": {f"{a} · {b}": {"n": int(v.n), "monto": _p(v.c)} for (a, b), v in flujo.iterrows()},
        "por_revisar": int(mov.requiere_revision.sum()),
        "ganancia_por_estado": _por_estado(r.ganancia),
        "fuera_del_reporte": {
            f"{a} · {b}": {"movimientos": int(v.movimientos), "ordenes": int(v.ordenes), "neto": _p(v.neto_c)}
            for (a, b), v in r.fuera_del_reporte.groupby(["motivo", "concepto"])
            .agg(movimientos=("mov_id", "size"), ordenes=("orden_id", "nunique"), neto_c=("neto_c", "sum"))
            .iterrows()
        },
    }
    if r.sin_recaudo is not None:
        out["sin_recaudo_cobro"] = r.sin_recaudo.estado_cobro.value_counts().to_dict()
        out["sin_recaudo_reembolso"] = _por_estado(r.sin_recaudo, "estado_reembolso")
        out["devolucion_por_estado"] = _por_estado(r.devoluciones)
    if r.fulfillment is not None:
        out["fulfillment_por_estado"] = _por_estado(r.fulfillment)
    return out
