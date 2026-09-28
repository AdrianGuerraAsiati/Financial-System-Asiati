"""Lectura de las exportaciones de Dropi a tablas normalizadas.

wallet  -> un movimiento por fila, monto en centavos enteros
ordenes -> una fila por orden (el reporte trae una fila por línea de producto)
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from . import normalizar as n

_ORDEN_EN_TEXTO = re.compile(r"ORDEN ID:?\s*\*?(\d+)")


class ColumnasFaltantesError(ValueError):
    def __init__(self, archivo: str, faltantes: list[str]):
        self.faltantes = faltantes
        super().__init__(
            f"Al archivo de {archivo} le faltan columnas: {', '.join(faltantes)}. "
            "Vuelve a descargar el reporte completo desde Dropi."
        )


def _exigir(df: pd.DataFrame, columnas: list[str], archivo: str) -> None:
    faltantes = [c for c in columnas if c not in df.columns]
    if faltantes:
        raise ColumnasFaltantesError(archivo, faltantes)


def leer_wallet(crudo: pd.DataFrame, params: dict) -> pd.DataFrame:
    c = params["columnas_wallet"]
    _exigir(crudo, [c["id"], c["fecha"], c["tipo"], c["monto"], c["monto_previo"], c["descripcion"]], "la wallet")

    w = pd.DataFrame(
        {
            "mov_id": crudo[c["id"]].astype("int64"),
            "fecha": n.fecha(crudo[c["fecha"]], c["fecha_formato"]),
            "tipo": crudo[c["tipo"]].map(n.texto),
            "monto_c": crudo[c["monto"]].map(n.centavos).astype("int64"),
            "previo_c": crudo[c["monto_previo"]].map(n.centavos).astype("int64"),
            "orden_id": crudo[c["orden_id"]].map(n.orden_id) if c["orden_id"] in crudo else None,
            "guia": crudo[c["guia"]].astype("string") if c["guia"] in crudo else None,
            "descripcion": crudo[c["descripcion"]].fillna("").astype(str),
            "descripcion_norm": crudo[c["descripcion"]].map(n.texto),
            "actor": crudo[c["actor"]].fillna("") if c["actor"] in crudo else "",
            "cuenta_retiro": crudo[c["cuenta_retiro"]] if c["cuenta_retiro"] in crudo else np.nan,
        }
    )
    # Si el ID de orden no viene en su columna, se toma de la descripción ("ORDEN ID: 123").
    faltante = w["orden_id"].isna()
    w.loc[faltante, "orden_id"] = w.loc[faltante, "descripcion_norm"].map(
        lambda s: (m.group(1) if (m := _ORDEN_EN_TEXTO.search(s)) else None)
    )
    w["signo"] = np.where(w["tipo"] == "ENTRADA", 1, -1)
    w["neto_c"] = w["monto_c"] * w["signo"]
    # El saldo solo cuadra en el orden del ID del movimiento: la fecha viene al minuto.
    return w.sort_values("mov_id").reset_index(drop=True)


def leer_ordenes(crudo: pd.DataFrame, params: dict) -> pd.DataFrame:
    c = params["columnas_ordenes"]
    _exigir(
        crudo,
        [c["orden_id"], c["estatus"], c["tipo_envio"], c["transportadora"], c["bodega"], c["fecha_guia"]],
        "órdenes",
    )
    f_estado = c["fechas_estado_formato"]
    base = pd.DataFrame(
        {
            "orden_id": crudo[c["orden_id"]].map(n.orden_id),
            "guia": crudo[c["guia"]].astype("string"),
            "estatus": crudo[c["estatus"]].map(n.texto),
            "tipo_envio": crudo[c["tipo_envio"]].map(n.texto),
            "transportadora": crudo[c["transportadora"]].map(n.texto),
            "bodega": crudo[c["bodega"]].map(n.texto),
            "fecha_orden": n.fecha(crudo[c["fecha_orden"]], c["fecha_orden_formato"]),
            "fecha_guia": n.fecha(crudo[c["fecha_guia"]], f_estado),
            "fecha_entregado": n.fecha(crudo[c["fecha_entregado"]], f_estado),
            "fecha_devolucion": n.fecha(crudo[c["fecha_devolucion"]], f_estado),
            "marca_blanca": crudo[c["marca_blanca"]].map(n.texto) if c.get("marca_blanca") in crudo else None,
        }
    )
    ordenes = base.groupby("orden_id", sort=True).agg(
        guia=("guia", "first"),
        estatus=("estatus", "first"),
        tipo_envio=("tipo_envio", "first"),
        transportadora=("transportadora", "first"),
        bodega=("bodega", "first"),
        fecha_orden=("fecha_orden", "first"),
        fecha_guia=("fecha_guia", "first"),
        fecha_entregado=("fecha_entregado", "first"),
        fecha_devolucion=("fecha_devolucion", "first"),
        marca_blanca=("marca_blanca", "first"),
        lineas=("estatus", "size"),
    )
    ordenes["fecha_cierre"] = ordenes["fecha_entregado"].fillna(ordenes["fecha_devolucion"])
    return ordenes
