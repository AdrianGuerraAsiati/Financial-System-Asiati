from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth.dependencias import Acceso, requiere
from app.core.cargas.errors import ContextoCargaInvalidoError
from app.core.hallazgos import Hallazgo
from app.core.periodos.errors import PeriodoCerradoError
from app.core.session import obtener_session

from .integracion import (
    CargaDuplicadaError,
    EjecucionWallet,
    catalogo_de_empresa,
    ejecutar_y_persistir_pagos,
    ejecutar_y_persistir_tienda,
    listar_hallazgos_wallet,
)


router = APIRouter(prefix="/wallets", tags=["wallets"])


def _empresa_de_query(empresa_id: int) -> int:
    return empresa_id


def _empresa_de_form(empresa_id: int = Form(...)) -> int:
    return empresa_id


ejecutar_conciliacion = requiere("conciliacion.ejecutar", empresa_de=_empresa_de_form)
ver_conciliacion = requiere("conciliacion.ver", empresa_de=_empresa_de_query)


def _ejecutar(session: Session, accion: Callable[[], EjecucionWallet]) -> dict[str, object]:
    try:
        ejecucion = accion()
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                "Este archivo de wallet ya fue cargado para la empresa. "
                "Usa una exportación nueva o consulta la conciliación existente."
            ),
        ) from exc
    except (CargaDuplicadaError, PeriodoCerradoError) as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ContextoCargaInvalidoError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        session.rollback()
        raise

    return {
        "bloqueado": ejecucion.bloqueado,
        "c0": ejecucion.c0,
        "cargas": {
            "wallet_id": ejecucion.carga_wallet_id,
            "ordenes_id": ejecucion.carga_ordenes_id,
            "ordenes_reutilizadas": ejecucion.ordenes_reutilizadas,
        },
        "hallazgos_creados": ejecucion.hallazgos_creados,
        "hallazgos_por_gravedad": ejecucion.hallazgos_por_gravedad,
        "resumen": ejecucion.resumen,
    }


def _hallazgo_json(hallazgo: Hallazgo) -> dict[str, object]:
    evidencia = hallazgo.evidencia or {}
    return {
        "id": hallazgo.id,
        "codigo_regla": hallazgo.codigo_regla,
        "descripcion": hallazgo.descripcion,
        "gravedad": evidencia.get("gravedad"),
        "critico": hallazgo.critico,
        "resuelto": hallazgo.resuelto,
        "estado": hallazgo.estado,
        "evidencia": evidencia,
    }


def _listar(session: Session, **filtros) -> list[dict[str, object]]:
    try:
        hallazgos = listar_hallazgos_wallet(session, **filtros)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_hallazgo_json(h) for h in hallazgos]


@router.get("/catalogo")
def consultar_catalogo(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_conciliacion),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    try:
        return catalogo_de_empresa(session, empresa_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tiendas/conciliar", status_code=201)
def conciliar_tienda(
    empresa_id: int = Form(...),
    _acceso: Acceso = Depends(ejecutar_conciliacion),
    periodo_id: int = Form(...),
    tienda: str = Form(...),
    fuente_wallet_id: int = Form(...),
    fuente_ordenes_id: int = Form(...),
    corte_ordenes: str | None = Form(None),
    wallet: UploadFile = File(...),
    ordenes: UploadFile = File(...),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    wallet_contenido = wallet.file.read()
    ordenes_contenido = ordenes.file.read()
    return _ejecutar(
        session,
        lambda: ejecutar_y_persistir_tienda(
            session,
            empresa_id=empresa_id,
            periodo_id=periodo_id,
            tienda_email=tienda,
            fuente_wallet_id=fuente_wallet_id,
            fuente_ordenes_id=fuente_ordenes_id,
            wallet_contenido=wallet_contenido,
            ordenes_contenido=ordenes_contenido,
            nombre_ordenes=ordenes.filename,
            corte=corte_ordenes,
        ),
    )


@router.get("/tiendas/hallazgos")
def consultar_hallazgos_tiendas(
    empresa_id: int,
    periodo_id: int,
    tienda: str | None = None,
    todas_las_cargas: bool = False,
    _acceso: Acceso = Depends(ver_conciliacion),
    session: Session = Depends(obtener_session),
) -> list[dict[str, object]]:
    return _listar(
        session,
        empresa_id=empresa_id,
        periodo_id=periodo_id,
        prefijo="TIENDA",
        wallet=tienda,
        todas_las_cargas=todas_las_cargas,
    )


@router.post("/pagos/conciliar", status_code=201)
def conciliar_pagos(
    empresa_id: int = Form(...),
    _acceso: Acceso = Depends(ejecutar_conciliacion),
    periodo_id: int = Form(...),
    wallet_pagos: str = Form(...),
    fuente_wallet_id: int = Form(...),
    wallet: UploadFile = File(...),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    wallet_contenido = wallet.file.read()
    return _ejecutar(
        session,
        lambda: ejecutar_y_persistir_pagos(
            session,
            empresa_id=empresa_id,
            periodo_id=periodo_id,
            wallet_email=wallet_pagos,
            fuente_wallet_id=fuente_wallet_id,
            wallet_contenido=wallet_contenido,
        ),
    )


@router.get("/pagos/hallazgos")
def consultar_hallazgos_pagos(
    empresa_id: int,
    periodo_id: int,
    wallet_pagos: str | None = None,
    todas_las_cargas: bool = False,
    _acceso: Acceso = Depends(ver_conciliacion),
    session: Session = Depends(obtener_session),
) -> list[dict[str, object]]:
    return _listar(
        session,
        empresa_id=empresa_id,
        periodo_id=periodo_id,
        prefijo="PAGOS",
        wallet=wallet_pagos,
        todas_las_cargas=todas_las_cargas,
    )
