"""Órdenes de una tienda: filtra las líneas que le tocan según su rol y agrupa por orden.

- DROPSHIPPER: líneas donde la tienda es el dropshipper (columna EMAIL).
- PROVEEDOR:   líneas donde la tienda es el proveedor (columna PROVEEDOR EMAIL). Una orden puede
               traer productos de varios proveedores: solo cuentan las líneas propias.

Montos en centavos enteros. El reporte trae una fila por línea de producto.
"""
from __future__ import annotations

import pandas as pd

from ..wiilog import normalizar as n
from ..wiilog.carga import _exigir

MONTOS = ["ganancia_dropshipper", "ganancia_proveedor", "precio_proveedor_x_cantidad", "precio_flete", "valor_compra"]


def leer_ordenes_tienda(crudo: pd.DataFrame, params: dict, tienda: dict) -> pd.DataFrame:
    c = params["columnas_ordenes"]
    email_col = c["email_dropshipper"] if tienda["rol"] == "DROPSHIPPER" else c["email_proveedor"]
    _exigir(crudo, [c["orden_id"], c["estatus"], c["tipo_envio"], email_col] + [c[m] for m in MONTOS], "órdenes")

    mia = crudo[crudo[email_col].map(n.texto) == n.texto(tienda["usuario_email"])]
    fe = c["fechas_estado_formato"]
    base = pd.DataFrame(
        {
            "orden_id": mia[c["orden_id"]].map(n.orden_id),
            "estatus": mia[c["estatus"]].map(n.texto),
            "tipo_envio": mia[c["tipo_envio"]].map(n.texto),
            "transportadora": mia[c["transportadora"]].map(n.texto),
            "bodega": mia[c["bodega"]].map(n.texto),
            "fecha_guia": n.fecha(mia[c["fecha_guia"]], fe),
            "fecha_entregado": n.fecha(mia[c["fecha_entregado"]], fe),
            "fecha_devolucion": n.fecha(mia[c["fecha_devolucion"]], fe),
            "contraparte": mia[c["email_proveedor"] if tienda["rol"] == "DROPSHIPPER" else c["email_dropshipper"]]
            .astype(str)
            .str.lower(),
            **{f"{m}_c": mia[c[m]].map(n.centavos) for m in MONTOS},
        }
    )
    agg = {
        k: (k, "first")
        for k in ["estatus", "tipo_envio", "transportadora", "bodega", "fecha_guia", "fecha_entregado", "fecha_devolucion", "contraparte"]
    }
    agg.update({f"{m}_c": (f"{m}_c", "sum") for m in MONTOS})
    agg["lineas"] = ("estatus", "size")
    return base.groupby("orden_id", sort=True).agg(**agg)


def fecha_reporte(crudo: pd.DataFrame, params: dict) -> pd.Timestamp:
    """Fin del día de la FECHA DE REPORTE. Un pago posterior no puede validarse contra este reporte."""
    c = params["columnas_ordenes"]
    f = pd.to_datetime(crudo[c["fecha_reporte"]].iloc[0], format=c["fecha_reporte_formato"])
    return f + pd.Timedelta(1, unit="D") - pd.Timedelta(1, unit="min")
