from __future__ import annotations

from collections import Counter
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth.dependencias import Acceso, requiere

from .agrupacion import agrupar_ocs
from .calidad import evaluar_calidad_lineas
from .dominio import LineaCompra
from .google_sheets import (
    ConfiguracionComprasGoogleSheetsError,
    EsquemaComprasInvalidoError,
    FuenteComprasGoogleSheets,
    construir_fuente_compras_desde_entorno,
)
from .normalizacion import normalizar_etiqueta


router = APIRouter(prefix="/compras", tags=["compras"])


def _empresa_de_query(empresa_id: int) -> int:
    return empresa_id


ver_compras = requiere("compras.ver", empresa_de=_empresa_de_query)


@lru_cache(maxsize=1)
def obtener_fuente_compras() -> FuenteComprasGoogleSheets:
    """Fuente compartida para reutilizar el snapshot entre requests."""
    try:
        return construir_fuente_compras_desde_entorno()
    except ConfiguracionComprasGoogleSheetsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _listar_seguro(
    fuente: FuenteComprasGoogleSheets,
    *,
    empresa_id: int,
) -> tuple[LineaCompra, ...]:
    try:
        return fuente.listar(empresa_id=empresa_id)
    except (ConfiguracionComprasGoogleSheetsError, EsquemaComprasInvalidoError) as exc:
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
    lineas = _listar_seguro(fuente, empresa_id=empresa_id)
    filtradas = _filtrar(lineas, pais=pais, estado=estado, oc=oc)
    pagina = filtradas[offset : offset + limit]

    return {
        "total": len(filtradas),
        "offset": offset,
        "limit": limit,
        "items": [linea.como_dict() for linea in pagina],
    }


@router.get("/ocs")
def listar_ocs_compras(
    empresa_id: int,
    pais: str | None = None,
    q: str | None = None,
    mixtas: bool | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    _acceso: Acceso = Depends(ver_compras),
    fuente: FuenteComprasGoogleSheets = Depends(obtener_fuente_compras),
) -> dict[str, object]:
    lineas = _listar_seguro(fuente, empresa_id=empresa_id)
    ocs = list(agrupar_ocs(lineas))

    if pais:
        pais_norm = normalizar_etiqueta(pais)
        ocs = [oc for oc in ocs if oc.pais == pais_norm]

    if q:
        termino = normalizar_etiqueta(q)
        ocs = [
            oc
            for oc in ocs
            if termino in normalizar_etiqueta(oc.numero_oc)
            or any(termino in normalizar_etiqueta(p) for p in oc.proveedores)
        ]

    if mixtas is not None:
        ocs = [
            oc
            for oc in ocs
            if (
                oc.estado_mixto
                or oc.proveedor_mixto
                or oc.transporte_mixto
            )
            is mixtas
        ]

    pagina = ocs[offset : offset + limit]
    return {
        "total": len(ocs),
        "offset": offset,
        "limit": limit,
        "items": [oc.como_dict() for oc in pagina],
    }


@router.get("/catalogos")
def catalogos_observados(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_compras),
    fuente: FuenteComprasGoogleSheets = Depends(obtener_fuente_compras),
) -> dict[str, object]:
    lineas = _listar_seguro(fuente, empresa_id=empresa_id)

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


@router.get("/calidad")
def calidad_fuente(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_compras),
    fuente: FuenteComprasGoogleSheets = Depends(obtener_fuente_compras),
) -> dict[str, object]:
    lineas = _listar_seguro(fuente, empresa_id=empresa_id)
    reglas = evaluar_calidad_lineas(lineas)

    return {
        "lineas_evaluadas": len(lineas),
        "reglas_con_resultados": len(reglas),
        "observaciones": [regla.como_dict() for regla in reglas],
        "nota": (
            "Estas observaciones no modifican la fuente ni implican por sí solas "
            "un error de negocio."
        ),
    }


@router.get("/fuente/estado")
def estado_fuente(
    empresa_id: int,
    forzar_lectura: bool = False,
    _acceso: Acceso = Depends(ver_compras),
    fuente: FuenteComprasGoogleSheets = Depends(obtener_fuente_compras),
) -> dict[str, object]:
    try:
        snapshot = fuente.obtener_snapshot(
            empresa_id=empresa_id,
            forzar_lectura=forzar_lectura,
        )
    except ConfiguracionComprasGoogleSheetsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "estado": "OK" if snapshot.esquema_valido else "DEGRADADO",
        "solo_lectura": True,
        "lineas": len(snapshot.lineas),
        "cargado_en": snapshot.cargado_en.isoformat(),
        "cache": fuente.estado_cache(),
        "hojas": [
            diagnostico.como_dict()
            for diagnostico in snapshot.diagnosticos
        ],
    }
