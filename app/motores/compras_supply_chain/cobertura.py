from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .dominio import LineaCompra
from .kpis import ESTADOS_ACTIVOS_TABLERO_ACTUAL


_ESTADOS_ACTIVOS = frozenset(ESTADOS_ACTIVOS_TABLERO_ACTUAL)


@dataclass(frozen=True)
class CampoCobertura:
    codigo: str
    nombre: str
    atributo: str


CAMPOS_COBERTURA: tuple[CampoCobertura, ...] = (
    CampoCobertura("proveedor", "Proveedor", "proveedor"),
    CampoCobertura("sku", "SKU", "sku"),
    CampoCobertura(
        "numero_factura_proveedor",
        "Factura proveedor",
        "numero_factura_proveedor",
    ),
    CampoCobertura(
        "valor_total_compra_usd",
        "Valor total compra USD",
        "valor_total_compra_usd_origen",
    ),
    CampoCobertura(
        "valor_oci_ddp",
        "Valor OCI/DDP",
        "valor_oci_ddp_origen",
    ),
    CampoCobertura(
        "fecha_abono_compra",
        "Fecha abono compra",
        "fecha_abono_compra",
    ),
    CampoCobertura(
        "fecha_pago_total_compra",
        "Fecha pago total compra",
        "fecha_pago_total_compra",
    ),
    CampoCobertura(
        "fecha_entrega_proveedor_estimada",
        "Fecha entrega proveedor estimada",
        "fecha_entrega_proveedor_estimada",
    ),
    CampoCobertura(
        "fecha_fin_produccion",
        "Fecha fin producción",
        "fecha_fin_produccion",
    ),
    CampoCobertura(
        "documento_transporte",
        "Documento transporte",
        "documento_transporte",
    ),
    CampoCobertura("etd", "ETD", "etd"),
    CampoCobertura("eta", "ETA", "eta"),
    CampoCobertura(
        "fecha_entrega_bodega_destino",
        "Fecha entrega bodega destino",
        "fecha_entrega_bodega_destino",
    ),
    CampoCobertura(
        "factura_destino",
        "Factura destino",
        "factura_destino",
    ),
    CampoCobertura(
        "fecha_solicitud_pago_abono",
        "Fecha solicitud pago abono",
        "fecha_solicitud_pago_abono",
    ),
)


def _segmento(lineas: Iterable[LineaCompra]) -> dict[str, object]:
    filas = tuple(lineas)
    total = len(filas)
    campos: dict[str, object] = {}

    for campo in CAMPOS_COBERTURA:
        presentes = sum(
            1
            for linea in filas
            if str(getattr(linea, campo.atributo) or "").strip()
        )
        faltantes = total - presentes
        cobertura = (
            "0.00"
            if total == 0
            else format((presentes * 100) / total, ".2f")
        )
        campos[campo.codigo] = {
            "nombre": campo.nombre,
            "presentes": presentes,
            "faltantes": faltantes,
            "cobertura_pct": cobertura,
        }

    return {
        "lineas": total,
        "campos": campos,
    }


def resumen_cobertura(
    lineas: Iterable[LineaCompra],
) -> dict[str, object]:
    filas = tuple(lineas)
    activas = tuple(
        linea
        for linea in filas
        if linea.estado_normalizado in _ESTADOS_ACTIVOS
    )
    entregadas = tuple(
        linea
        for linea in filas
        if linea.estado_normalizado == "ENTREGADO"
    )

    return {
        "general": _segmento(filas),
        "poblacion_actual": _segmento(activas),
        "entregado": _segmento(entregadas),
        "nota": (
            "La cobertura describe presencia o ausencia de datos. "
            "Un campo vacío no se clasifica automáticamente como error contable."
        ),
    }
