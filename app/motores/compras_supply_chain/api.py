from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth.dependencias import Acceso, requiere

from .dominio import LineaCompra
from .google_sheets import (
    ConfiguracionComprasGoogleSheetsError,
    FuenteComprasGoogleSheets,
    construir_fuente_compras_desde_entorno,
)
from .normalizacion import normalizar_etiqueta


router = APIRouter(prefix="/compras", tags=["compras"])


def _empresa_de_query(empresa_id: int) -> int:
    return empresa_id


ver_compras = requiere("compras.ver", empresa_de=_empresa_de_query)


def obtener_fuente_compras() -> FuenteComprasGoogleSheets:
    try:
        return construir_fuente_compras_desde_entorno()
    except ConfiguracionComprasGoogleSheetsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _filtrar(
    lineas: tuple[LineaCompra, ...],
    *,
    pais: str | None,
    estado: str | None,
    oc: str | None,
) -> list[LineaCompra]:
    resultado = list(lineas)

    if pais:
        pais_norm = normalizar_etiqueta(pais)
        resultado = [linea for linea in resultado if linea.pais == pais_norm]

    if estado:
        estado_norm = normalizar_etiqueta(estado)
        resultado = [
            linea
            for linea in resultado
            if linea.estado_normalizado == estado_norm
        ]

    if oc:
        oc_norm = normalizar_etiqueta(oc)
        resultado = [
            linea
            for linea in resultado
            if normalizar_etiqueta(linea.numero_oc) == oc_norm
        ]

    return resultado


@router.get("/lineas")
def listar_lineas_compras(
    empresa_id: int,
    pais: str | None = None,
    estado: str | None = None,
    oc: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    _acceso: Acceso = Depends(ver_compras),
    fuente: FuenteComprasGoogleSheets = Depends(obtener_fuente_compras),
) -> dict[str, object]:
    try:
        lineas = fuente.listar(empresa_id=empresa_id)
    except ConfiguracionComprasGoogleSheetsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    filtradas = _filtrar(lineas, pais=pais, estado=estado, oc=oc)
    pagina = filtradas[offset : offset + limit]

    return {
        "total": len(filtradas),
        "offset": offset,
        "limit": limit,
        "items": [linea.como_dict() for linea in pagina],
    }


@router.get("/catalogos")
def catalogos_observados(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_compras),
    fuente: FuenteComprasGoogleSheets = Depends(obtener_fuente_compras),
) -> dict[str, object]:
    try:
        lineas = fuente.listar(empresa_id=empresa_id)
    except ConfiguracionComprasGoogleSheetsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    estados = Counter(
        linea.estado_normalizado or "(VACIO)"
        for linea in lineas
    )
    modos = Counter(
        linea.modo_transporte_normalizado or "(VACIO)"
        for linea in lineas
    )
    paises = Counter(linea.pais for linea in lineas)
    etapas = Counter(linea.etapa_logistica for linea in lineas)

    pendientes = Counter(
        linea.estado_normalizado or "(VACIO)"
        for linea in lineas
        if linea.etapa_logistica == "POR_DEFINIR"
    )

    return {
        "lineas": len(lineas),
        "paises": dict(sorted(paises.items())),
        "estados": dict(sorted(estados.items())),
        "modos_transporte": dict(sorted(modos.items())),
        "etapas_logisticas": dict(sorted(etapas.items())),
        "estados_por_definir": dict(sorted(pendientes.items())),
    }
