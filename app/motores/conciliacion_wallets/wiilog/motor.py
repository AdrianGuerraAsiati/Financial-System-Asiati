"""Punto de entrada del motor para la wallet de Wiilog. Python puro: DataFrames y un dict de parámetros.

    resultado = conciliar_wallet_wiilog(ordenes_crudo, wallet_crudo, params, periodo_inicio, periodo_fin)

El núcleo (FastAPI + Postgres) se encarga de guardar cargas, movimientos, resultados y hallazgos.
Este módulo no sabe nada de base de datos.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from . import carga, flete, fulfillment, movimientos
from . import normalizar as n


@dataclass
class ResultadoWiilog:
    bloqueado: bool
    chequeos: list
    movimientos: pd.DataFrame | None = None
    ff: pd.DataFrame | None = None
    ff_fuera: pd.DataFrame | None = None
    flete: pd.DataFrame | None = None
    flete_fuera: pd.DataFrame | None = None
    resumen: dict = field(default_factory=dict)


def conciliar_wallet_wiilog(ordenes_crudo, wallet_crudo, params, periodo_inicio, periodo_fin) -> ResultadoWiilog:
    wallet = carga.leer_wallet(wallet_crudo, params)
    chequeos = movimientos.validar_integridad(wallet, periodo_inicio, periodo_fin)
    if any(c.estado == "BLOQUEADO" for c in chequeos):
        return ResultadoWiilog(bloqueado=True, chequeos=chequeos)

    ordenes = carga.leer_ordenes(ordenes_crudo, params)
    mov = movimientos.clasificar(wallet, params)
    mov = movimientos.emparejar_cruces(mov, params)
    corte = mov["fecha"].max()

    ff, ff_fuera = fulfillment.conciliar(ordenes, mov, params, corte)
    fl, fl_fuera = flete.conciliar(ordenes, mov, params, corte)
    return ResultadoWiilog(
        bloqueado=False,
        chequeos=chequeos,
        movimientos=mov,
        ff=ff,
        ff_fuera=ff_fuera,
        flete=fl,
        flete_fuera=fl_fuera,
        resumen=resumir(mov, ff, ff_fuera, fl, fl_fuera, corte),
    )


def _p(c) -> str:
    return str(n.pesos(int(c)))


def resumir(mov, ff, ff_fuera, fl, fl_fuera, corte) -> dict:
    def por_estado(df, col):
        g = df.groupby(col).agg(ordenes=(col, "size"), en_juego_c=("monto_en_juego_c", "sum"))
        return {k: {"ordenes": int(v.ordenes), "monto_en_juego": _p(v.en_juego_c)} for k, v in g.iterrows()}

    flujo = mov.groupby(["flujo", "concepto"]).agg(n=("mov_id", "size"), c=("monto_c", "sum"))
    return {
        "fecha_corte": str(corte),
        "movimientos": {f"{a} · {b}": {"n": int(v.n), "monto": _p(v.c)} for (a, b), v in flujo.iterrows()},
        "por_revisar": int((mov.estado_categoria != "AUTO").sum()),
        "ff_por_estado": por_estado(ff[ff.bodega_wiilog], "estado_ff"),
        "ff_no_cobrado_por_bodega": ff[ff.estado_ff == "NO_COBRADO"].groupby("bodega").size().to_dict(),
        "ff_cobros_sin_orden_en_reporte": ff_fuera.groupby("estado_ff").agg(n=("ff_neto_c", "size"), c=("ff_neto_c", "sum")).apply(
            lambda v: {"ordenes": int(v.n), "monto": _p(v.c)}, axis=1
        ).to_dict(),
        "flete_por_estado": por_estado(fl, "estado_flete"),
        "flete_cobros_sin_orden_en_reporte": {"ordenes": int(len(fl_fuera)), "monto": _p(fl_fuera.flete_neto_c.sum())},
    }
