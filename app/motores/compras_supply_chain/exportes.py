from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Iterable

from .agrupacion import agrupar_ocs
from .atencion import evaluar_puntos_atencion
from .dominio import LineaCompra
from .kpis import calcular_familias_monetarias
from .contrato import DiagnosticoEsquema


def _csv_bytes(encabezados: list[str], filas: Iterable[list[object]]) -> bytes:
    salida = io.StringIO(newline="")
    escritor = csv.writer(salida)
    escritor.writerow(encabezados)
    for fila in filas:
        escritor.writerow(fila)
    return salida.getvalue().encode("utf-8-sig")


def _csv_lineas(lineas: tuple[LineaCompra, ...]) -> bytes:
    return _csv_bytes(
        [
            "pais",
            "hoja_fuente",
            "fila_fuente",
            "numero_oc",
            "oc_identificada",
            "cliente",
            "sku",
            "descripcion",
            "proveedor",
            "estado_origen",
            "estado_normalizado",
            "etapa_logistica",
            "situacion_operativa",
            "modo_transporte_origen",
            "modo_transporte_normalizado",
            "documento_transporte",
            "etd",
            "eta",
            "fecha_entrega_bodega_destino",
            "valor_total_compra_usd_origen",
            "valor_oci_ddp_origen",
        ],
        (
            [
                linea.pais,
                linea.hoja_fuente,
                linea.fila_fuente,
                linea.numero_oc,
                linea.oc_identificada,
                linea.cliente,
                linea.sku,
                linea.descripcion,
                linea.proveedor,
                linea.estado_origen,
                linea.estado_normalizado,
                linea.etapa_logistica,
                linea.situacion_operativa,
                linea.modo_transporte_origen,
                linea.modo_transporte_normalizado,
                linea.documento_transporte,
                linea.etd,
                linea.eta,
                linea.fecha_entrega_bodega_destino,
                linea.valor_total_compra_usd_origen,
                linea.valor_oci_ddp_origen,
            ]
            for linea in lineas
        ),
    )


def _csv_ocs(lineas: tuple[LineaCompra, ...]) -> bytes:
    ocs = agrupar_ocs(lineas)
    return _csv_bytes(
        [
            "clave",
            "pais",
            "numero_oc",
            "oc_identificada",
            "lineas",
            "proveedores",
            "estados",
            "etapas_logisticas",
            "modos_transporte",
            "estado_mixto",
            "proveedor_mixto",
            "transporte_mixto",
        ],
        (
            [
                oc.clave,
                oc.pais,
                oc.numero_oc,
                oc.oc_identificada,
                oc.lineas,
                " | ".join(oc.proveedores),
                " | ".join(oc.estados),
                " | ".join(oc.etapas_logisticas),
                " | ".join(oc.modos_transporte),
                oc.estado_mixto,
                oc.proveedor_mixto,
                oc.transporte_mixto,
            ]
            for oc in ocs
        ),
    )


def _csv_atencion(lineas: tuple[LineaCompra, ...]) -> bytes:
    puntos = evaluar_puntos_atencion(lineas)
    filas: list[list[object]] = []
    for punto in puntos:
        if not punto.muestras:
            filas.append(
                [
                    punto.codigo,
                    punto.titulo,
                    punto.categoria,
                    punto.cantidad,
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )
            continue
        for muestra in punto.muestras:
            filas.append(
                [
                    punto.codigo,
                    punto.titulo,
                    punto.categoria,
                    punto.cantidad,
                    muestra.pais,
                    muestra.numero_oc,
                    muestra.hoja_fuente,
                    muestra.fila_fuente,
                    muestra.evidencia,
                ]
            )
    return _csv_bytes(
        [
            "codigo",
            "titulo",
            "categoria",
            "cantidad_total",
            "pais_muestra",
            "oc_muestra",
            "hoja_muestra",
            "fila_muestra",
            "evidencia_muestra",
        ],
        filas,
    )


def _csv_kpis(
    lineas: tuple[LineaCompra, ...],
    diagnosticos: tuple[DiagnosticoEsquema, ...],
) -> bytes:
    familias = calcular_familias_monetarias(lineas, diagnosticos)
    filas: list[list[object]] = []
    for familia in familias:
        if not familia.disponible:
            filas.append(
                [
                    familia.familia.codigo,
                    familia.familia.nombre,
                    "NO_DISPONIBLE",
                    "",
                    "",
                    "",
                    ", ".join(familia.hojas_sin_campo),
                ]
            )
            continue
        assert familia.activo is not None
        filas.append(
            [
                familia.familia.codigo,
                familia.familia.nombre,
                "ACTIVO",
                familia.activo.lineas,
                familia.activo.lineas_con_valor,
                format(familia.activo.monto.quantize(__import__("decimal").Decimal("0.01")), "f"),
                "",
            ]
        )
        for estado, incluido, acumulado in familia.por_estado:
            filas.append(
                [
                    familia.familia.codigo,
                    familia.familia.nombre,
                    f"ESTADO:{estado}",
                    acumulado.lineas,
                    acumulado.lineas_con_valor,
                    format(acumulado.monto.quantize(__import__("decimal").Decimal("0.01")), "f"),
                    "incluido" if incluido else "fuera_poblacion_actual",
                ]
            )
    return _csv_bytes(
        [
            "familia",
            "nombre",
            "segmento",
            "lineas",
            "lineas_con_valor",
            "monto_usd",
            "nota",
        ],
        filas,
    )


def crear_zip_exportacion(
    lineas: tuple[LineaCompra, ...],
    diagnosticos: tuple[DiagnosticoEsquema, ...],
) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", compression=zipfile.ZIP_DEFLATED) as archivo:
        archivo.writestr("compras_lineas.csv", _csv_lineas(lineas))
        archivo.writestr("compras_ocs.csv", _csv_ocs(lineas))
        archivo.writestr("compras_puntos_atencion.csv", _csv_atencion(lineas))
        archivo.writestr("compras_kpis.csv", _csv_kpis(lineas, diagnosticos))
    return memoria.getvalue()
