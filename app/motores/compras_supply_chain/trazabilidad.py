from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

from .dominio import LineaCompra
from .fechas import parsear_fecha_fuente
from .normalizacion import normalizar_etiqueta


_HITOS: tuple[tuple[str, str, str], ...] = (
    ("ABONO_COMPRA", "Abono de compra", "fecha_abono_compra"),
    (
        "PAGO_TOTAL_COMPRA",
        "Pago total de compra",
        "fecha_pago_total_compra",
    ),
    (
        "ENTREGA_PROVEEDOR_ESTIMADA",
        "Entrega proveedor estimada",
        "fecha_entrega_proveedor_estimada",
    ),
    (
        "FIN_PRODUCCION",
        "Finalización de producción",
        "fecha_fin_produccion",
    ),
    (
        "INGRESO_BODEGA_ORIGEN",
        "Ingreso a bodega en origen",
        "fecha_ingreso_bodega_origen",
    ),
    ("CARGUE", "Cargue", "fecha_cargue"),
    ("ETD", "ETD", "etd"),
    ("ETA", "ETA", "eta"),
    ("NACIONALIZACION", "Nacionalización", "nacionalizacion"),
    (
        "ENTREGA_DESTINO",
        "Entrega a bodega destino",
        "fecha_entrega_bodega_destino",
    ),
)


def construir_timeline_oc(
    lineas: Iterable[LineaCompra],
    *,
    pais: str,
    numero_oc: str,
) -> dict[str, object]:
    pais_normalizado = normalizar_etiqueta(pais)
    oc_normalizada = normalizar_etiqueta(numero_oc)
    filtradas = tuple(
        linea
        for linea in lineas
        if linea.pais == pais_normalizado
        and normalizar_etiqueta(linea.numero_oc) == oc_normalizada
    )

    items: list[dict[str, object]] = []
    for linea in sorted(filtradas, key=lambda item: item.fila_fuente):
        hitos: list[dict[str, str]] = []
        for codigo, nombre, atributo in _HITOS:
            valor = str(getattr(linea, atributo) or "").strip()
            if not valor:
                continue
            hitos.append(
                {
                    "codigo": codigo,
                    "nombre": nombre,
                    "fecha_origen": valor,
                }
            )
        items.append(
            {
                "pais": linea.pais,
                "hoja_fuente": linea.hoja_fuente,
                "fila_fuente": linea.fila_fuente,
                "numero_oc": linea.numero_oc,
                "sku": linea.sku,
                "descripcion": linea.descripcion,
                "proveedor": linea.proveedor,
                "estado": linea.estado_normalizado,
                "modo_transporte": linea.modo_transporte_normalizado,
                "documento_transporte": linea.documento_transporte,
                "hitos": hitos,
            }
        )

    return {
        "pais": pais_normalizado,
        "numero_oc": numero_oc,
        "lineas": len(items),
        "items": items,
        "nota": (
            "Los hitos se muestran por línea de fuente. "
            "No se inventa una fecha única agregada para la OC."
        ),
    }


def proximas_llegadas(
    lineas: Iterable[LineaCompra],
    *,
    hoy: date | None = None,
    dias: int = 30,
    pais: str | None = None,
) -> dict[str, object]:
    if dias < 0:
        raise ValueError("dias debe ser mayor o igual a cero.")

    fecha_inicio = hoy or date.today()
    fecha_fin = fecha_inicio + timedelta(days=dias)
    pais_normalizado = normalizar_etiqueta(pais) if pais else None

    items: list[tuple[date, LineaCompra]] = []
    for linea in lineas:
        if pais_normalizado and linea.pais != pais_normalizado:
            continue
        if (
            linea.estado_normalizado == "ENTREGADO"
            or linea.situacion_operativa == "ANULADA"
            or linea.fecha_entrega_bodega_destino.strip()
        ):
            continue

        eta = parsear_fecha_fuente(linea.eta)
        if eta is None or eta < fecha_inicio or eta > fecha_fin:
            continue
        items.append((eta, linea))

    items.sort(
        key=lambda item: (
            item[0],
            item[1].pais,
            normalizar_etiqueta(item[1].numero_oc),
            item[1].fila_fuente,
        )
    )

    return {
        "desde": fecha_inicio.isoformat(),
        "hasta": fecha_fin.isoformat(),
        "dias": dias,
        "pais": pais_normalizado,
        "lineas": len(items),
        "items": [
            {
                "pais": linea.pais,
                "numero_oc": linea.numero_oc,
                "fila_fuente": linea.fila_fuente,
                "cliente": linea.cliente,
                "sku": linea.sku,
                "proveedor": linea.proveedor,
                "estado": linea.estado_normalizado,
                "modo_transporte": linea.modo_transporte_normalizado,
                "documento_transporte": linea.documento_transporte,
                "eta": eta.isoformat(),
                "dias_hasta_eta": (eta - fecha_inicio).days,
                "valor_total_compra_usd_origen": (
                    linea.valor_total_compra_usd_origen
                ),
                "valor_oci_ddp_origen": linea.valor_oci_ddp_origen,
            }
            for eta, linea in items
        ],
        "nota": (
            "Proyección descriptiva basada únicamente en ETA interpretable. "
            "No sustituye una promesa de entrega ni corrige la fuente."
        ),
    }
