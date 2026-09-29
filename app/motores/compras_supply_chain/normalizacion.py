from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from typing import Any

from .dominio import LineaCompra


HOJAS_POR_PAIS = {
    "CO": "INFORME CLIENTES (CO)",
    "EC": "INFORME CLIENTES (EC)",
    "CL": "INFORME CLIENTES (CL)",
}

_MAPA_ESTADOS_SEGUROS: dict[str, tuple[str, str]] = {
    "EN PRODUCCION": ("PRODUCCION", "NORMAL"),
    "EN BODEGA ASIATI YIWU": ("ORIGEN", "NORMAL"),
    "EN BODEGA ASIATI SHENZHEN": ("ORIGEN", "NORMAL"),
    "ENVIADO A DESTINO": ("TRANSITO", "NORMAL"),
    "EN NACIONALIZACION": ("NACIONALIZACION", "NORMAL"),
    "ENTREGADO": ("RECIBIDO", "NORMAL"),
    "ANULADA": ("SIN_ETAPA", "ANULADA"),
    "EN RECLAMACION": ("POR_DEFINIR", "RECLAMACION"),
}

_ESTADOS_PENDIENTES = {
    "EN OTM",
    "PENDIENTE DEPOSITO",
    "EN BODEGA ASIATI MIAMI",
    "ENVIADO A BODEGA ASIATI CHINA",
    "EN BODEGA PROVEEDOR",
    "PENDIENTE INVIMA",
    "DEVOLUCION",
}


def normalizar_etiqueta(valor: Any) -> str:
    texto = str(valor or "").strip()
    texto = " ".join(texto.split())
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.upper()


def normalizar_encabezado(valor: Any) -> str:
    texto = normalizar_etiqueta(valor)
    texto = re.sub(r"\s+", " ", texto)
    return texto


def clasificar_estado(estado_origen: Any) -> tuple[str, str, str]:
    normalizado = normalizar_etiqueta(estado_origen)
    if not normalizado:
        return "", "POR_DEFINIR", "POR_DEFINIR"

    if normalizado in _MAPA_ESTADOS_SEGUROS:
        etapa, situacion = _MAPA_ESTADOS_SEGUROS[normalizado]
        return normalizado, etapa, situacion

    if normalizado in _ESTADOS_PENDIENTES:
        return normalizado, "POR_DEFINIR", "POR_DEFINIR"

    return normalizado, "POR_DEFINIR", "POR_DEFINIR"


def normalizar_modo_transporte(valor: Any) -> str:
    normalizado = normalizar_etiqueta(valor)
    equivalencias = {
        "MARITIMA": "MARITIMO",
        "MARITIMO": "MARITIMO",
        "AEREA": "AEREO",
        "AEREO": "AEREO",
        "CASILLERO": "CASILLERO",
        "MUESTRA": "MUESTRA",
    }
    return equivalencias.get(normalizado, normalizado)


def _indice_fila(fila: Mapping[str, Any]) -> dict[str, Any]:
    return {
        normalizar_encabezado(clave): valor
        for clave, valor in fila.items()
        if normalizar_encabezado(clave)
    }


def _valor(indice: Mapping[str, Any], *aliases: str) -> str:
    for alias in aliases:
        clave = normalizar_encabezado(alias)
        if clave in indice:
            valor = indice[clave]
            return "" if valor is None else str(valor).strip()
    return ""


def _oc_identificada(numero_oc: str) -> bool:
    return normalizar_etiqueta(numero_oc) not in {"", "N/A", "NA"}


def normalizar_fila_compra(
    fila: Mapping[str, Any],
    *,
    pais: str,
    fila_fuente: int,
) -> LineaCompra:
    pais_normalizado = normalizar_etiqueta(pais)
    if pais_normalizado not in HOJAS_POR_PAIS:
        raise ValueError(f"País de hoja no soportado: {pais!r}")

    indice = _indice_fila(fila)

    numero_oc = _valor(indice, "NUMERO OC")
    estado_origen = _valor(indice, "ESTADO")
    estado_normalizado, etapa, situacion = clasificar_estado(estado_origen)
    modo_origen = _valor(indice, "MODO TRANSPORTE")

    entrega_destino = _valor(
        indice,
        "FECHA ENTREGA EN BODEGA BOGOTA",
        "FECHA ENTREGA EN BODEGA BOGOTÁ",
        "FECHA ENTREGA EN BODEGA QUITO",
        "FECHA ENTREGA EN BODEGA SANTIAGO",
        "FECHA ENTREGA A BODEGA EN BOG",
        "FECHA ENTREGA A BODEGA EN QUITO",
        "FECHA ENTREGA A BODEGA EN SANTIAGO",
        "FECHA ENTREGA BODEGA DESTINO",
    )

    return LineaCompra(
        pais=pais_normalizado,
        hoja_fuente=HOJAS_POR_PAIS[pais_normalizado],
        fila_fuente=fila_fuente,
        numero_oc=numero_oc,
        oc_identificada=_oc_identificada(numero_oc),
        cliente=_valor(indice, "CLIENTE"),
        sku=_valor(indice, "SKU"),
        descripcion=_valor(indice, "DESCRIPCION", "DESCRIPCIÓN"),
        proveedor=_valor(indice, "PROVEEDOR"),
        estado_origen=estado_origen,
        estado_normalizado=estado_normalizado,
        etapa_logistica=etapa,
        situacion_operativa=situacion,
        modo_transporte_origen=modo_origen,
        modo_transporte_normalizado=normalizar_modo_transporte(modo_origen),
        documento_transporte=_valor(
            indice,
            "DOCUMENTO DE TRANSPORTE",
            "DOC TRANSPORTE",
        ),
        etd=_valor(indice, "ETD"),
        eta=_valor(indice, "ETA"),
        fecha_entrega_bodega_destino=entrega_destino,
        valor_total_compra_usd_origen=_valor(
            indice,
            "VALOR TOTAL COMPRA USD",
        ),
        valor_oci_ddp_origen=_valor(indice, "VALOR OCI (DDP)"),
    )
