"""C0 (integridad), conceptos de la wallet, categoría por defecto y cruces neto cero."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import normalizar as n

# --------------------------------------------------------------------------- C0


@dataclass(frozen=True)
class Chequeo:
    codigo: str
    estado: str  # EN_ORDEN | BLOQUEADO | ADVERTENCIA
    mensaje: str
    detalle: dict = field(default_factory=dict)


def validar_integridad(wallet: pd.DataFrame, periodo_inicio, periodo_fin, tolerancia_c: int = 100) -> list[Chequeo]:
    """C0. Si algún chequeo queda BLOQUEADO, la conciliación no se ejecuta."""
    out: list[Chequeo] = []

    # a) continuidad del saldo: previo(i+1) == previo(i) + neto(i)
    esperado = wallet["previo_c"] + wallet["neto_c"]
    siguiente = wallet["previo_c"].shift(-1)
    quiebres = (siguiente - esperado).iloc[:-1].abs() > tolerancia_c
    n_quiebres = int(quiebres.sum())
    saldo_ini = int(wallet["previo_c"].iloc[0])
    saldo_fin = int(wallet["previo_c"].iloc[-1] + wallet["neto_c"].iloc[-1])
    cuadra = abs(saldo_ini + int(wallet["neto_c"].sum()) - saldo_fin) <= tolerancia_c
    out.append(
        Chequeo(
            "C0_SALDO",
            "EN_ORDEN" if n_quiebres == 0 and cuadra else "BLOQUEADO",
            "El saldo cuadra movimiento a movimiento."
            if n_quiebres == 0 and cuadra
            else f"El saldo no cuadra en {n_quiebres} puntos. El archivo puede estar incompleto: descárgalo de nuevo.",
            {
                "saldo_inicial": str(n.pesos(saldo_ini)),
                "entradas": str(n.pesos(int(wallet.loc[wallet.signo == 1, "monto_c"].sum()))),
                "salidas": str(n.pesos(int(wallet.loc[wallet.signo == -1, "monto_c"].sum()))),
                "saldo_final": str(n.pesos(saldo_fin)),
                "quiebres": n_quiebres,
            },
        )
    )

    # b) cobertura de fechas: el archivo cubre todos los días del período hasta el corte
    dias_archivo = set(wallet["fecha"].dt.normalize())
    fin = min(pd.Timestamp(periodo_fin), wallet["fecha"].max().normalize())
    dias_periodo = set(pd.date_range(pd.Timestamp(periodo_inicio), fin, freq="D"))
    faltan = sorted(d.date().isoformat() for d in dias_periodo - dias_archivo)
    out.append(
        Chequeo(
            "C0_COBERTURA",
            "EN_ORDEN" if not faltan else "ADVERTENCIA",
            "El archivo tiene movimientos todos los días del período."
            if not faltan
            else f"No hay movimientos en {len(faltan)} días del período. Confirma que el archivo esté completo.",
            {"dias_sin_movimientos": faltan, "desde": str(wallet["fecha"].min()), "hasta": str(wallet["fecha"].max())},
        )
    )
    return out


# ------------------------------------------------------------ conceptos y categoría

CATEGORIA_POR_CONCEPTO = {
    # concepto: (flujo, descripción, estado, observación obligatoria).
    # Ingreso/egreso, unidad de negocio y categoría salen del catálogo común (concepto_catalogo_comun).
    "FF_GUIA_GENERADA": ("INGRESO", "Fulfillment", "AUTO", False),
    "FF_CIERRE": ("INGRESO", "Fulfillment sin recaudo", "AUTO", False),
    "FF_OTRO_USUARIO": ("INGRESO", "Fulfillment órdenes fuera de marca blanca", "AUTO", False),
    "FF_CORRECCION": ("EGRESO", "Reverso de fulfillment", "AUTO", False),
    "FLETE_MB": ("INGRESO", "Comisión flete marca blanca", "AUTO", False),
    "CRUCE_RECARGA_IN": ("NETO_CERO", "Cruce de cartera Dropi", "AUTO", False),
    "CRUCE_DESCUENTO_IN": ("NETO_CERO", "Cruce de cartera Dropi", "AUTO", False),
    "CRUCE_RETIRO_OUT": ("NETO_CERO", "Cruce de cartera Dropi", "AUTO", False),
    "TRANSFERENCIA_RECIBIDA": ("INGRESO", "Transferencia recibida de usuario", "REVISAR", True),
    "RECARGA_RECIBIDA": ("INGRESO", "Recarga recibida", "REVISAR", True),
    "TRASLADO_WALLET_WIILOG": ("TRASLADO", "Traslado a wallet principal Wiilog", "AUTO", False),
    "TRANSFERENCIA_ENVIADA": ("EGRESO", "Transferencia a otro usuario por SUPER ADMIN", "REVISAR", True),
    # Decisión 6-oct: el retiro a banco no tiene unidad de negocio; la pone el conciliador.
    "RETIRO_BANCARIO": ("EGRESO", "Retiro a cuenta bancaria", "REVISAR", True),
    "SIN_CONCEPTO": ("PENDIENTE", None, "PENDIENTE", True),
}

# Dimensiones de las filas CRUCE_* del catálogo común: un cruce emparejado es neto cero.
DIMENSIONES_CRUCE = ("NETO_CERO", "FF", "CRUCE DE CARTERA DROPI")

_CORREO = re.compile(r"(?:USUARIO|USER)\s+([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})")


def _dimensiones_comunes(conceptos: pd.Series, params: dict, catalogo: dict | None) -> pd.DataFrame:
    """Ingreso/egreso, unidad y categoría desde la fila del catálogo común; vacío si no hay fila (SIN_CONCEPTO)."""
    columnas = ["ingreso_egreso", "unidad_negocio", "categoria"]
    if catalogo is None:
        return pd.DataFrame({c: [None] * len(conceptos) for c in columnas}, index=conceptos.index)
    por_codigo = {r["codigo"]: r for r in catalogo["conceptos"]}
    mapa = params.get("concepto_catalogo_comun", {})
    filas = conceptos.map(lambda c: por_codigo.get(mapa.get(c), {}))
    return pd.DataFrame({c: filas.map(lambda f, c=c: f.get(c)) for c in columnas}, index=conceptos.index)


def clasificar(wallet: pd.DataFrame, params: dict, catalogo: dict | None = None) -> pd.DataFrame:
    """Asigna concepto (primera regla que empareja gana) y las dimensiones del catálogo común."""
    reglas = params["conceptos_wallet"]
    w = wallet.copy()

    def concepto(fila) -> str:
        d = fila.descripcion_norm
        for r in reglas:
            if r["tipo"] != fila.tipo:
                continue
            if "requiere_columna" in r:
                if pd.notna(fila.cuenta_retiro):
                    return r["codigo"]
                continue
            if d.startswith(n.texto(r["empieza_con"])) and n.texto(r.get("contiene", "")) in d:
                return r["codigo"]
        return "SIN_CONCEPTO"

    w["concepto"] = [concepto(f) for f in w.itertuples(index=False)]
    w["tercero"] = w["descripcion_norm"].map(lambda s: (m.group(1).lower() if (m := _CORREO.search(s)) else None))
    cat = w["concepto"].map(CATEGORIA_POR_CONCEPTO)
    w["flujo"] = cat.map(lambda t: t[0])
    w[["ingreso_egreso", "unidad_negocio", "categoria"]] = _dimensiones_comunes(w["concepto"], params, catalogo)
    w["estado_categoria"] = cat.map(lambda t: t[2])
    w["requiere_observacion"] = cat.map(lambda t: t[3])
    w["observacion"] = ""
    w["cruce_id"] = pd.NA
    return w


def emparejar_cruces(w: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Empareja entradas y salidas del mismo valor dentro de la ventana: son puente, no plata de Wiilog."""
    cfg = params["cruces_neto_cero"]
    ventana = pd.Timedelta(int(cfg["ventana_minutos"]), unit="min")
    w = w.copy()
    usados: set[int] = set()
    cruce = 0
    for entrada_cod, salida_cod in cfg["emparejar"]:
        entradas = w[(w.concepto == entrada_cod) & ~w.index.isin(usados)]
        for i, e in entradas.iterrows():
            candidatas = w[
                (w.concepto == salida_cod)
                & ~w.index.isin(usados)
                & (w.monto_c == e.monto_c)
                & ((w.fecha - e.fecha).abs() <= ventana)
            ]
            if entrada_cod == "CRUCE_RECARGA_IN" and e.tercero:
                candidatas = candidatas[candidatas.tercero == e.tercero]
            if candidatas.empty:
                continue
            j = (candidatas.fecha - e.fecha).abs().idxmin()
            cruce += 1
            usados.update({i, j})
            for k in (i, j):
                w.at[k, "cruce_id"] = f"CRUCE-{cruce:03d}"
                w.at[k, "flujo"] = "NETO_CERO"
                w.at[k, "ingreso_egreso"], w.at[k, "unidad_negocio"], w.at[k, "categoria"] = DIMENSIONES_CRUCE
                w.at[k, "estado_categoria"] = "AUTO"
                w.at[k, "requiere_observacion"] = False
    # Un cruce sin pareja no es neto cero: se revisa.
    solos = w.concepto.str.startswith("CRUCE_") & w.cruce_id.isna()
    w.loc[solos, ["estado_categoria", "requiere_observacion"]] = ["REVISAR", True]
    return w
