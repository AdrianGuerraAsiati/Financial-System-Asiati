from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth.dependencias import Acceso, requiere
from app.core.cargas.errors import ContextoCargaInvalidoError
from app.core.periodos.errors import PeriodoCerradoError
from app.core.session import obtener_session

from ..plataforma.api import hallazgo_json
from .integracion import (
    MENSAJE_CONFIGURACION_FALTANTE,
    ConfiguracionWiilogFaltanteError,
    ejecutar_y_persistir_wiilog,
    listar_hallazgos_wiilog,
)


router = APIRouter(prefix="/wallets/wiilog", tags=["wallets"])


def _empresa_de_query(empresa_id: int) -> int:
    return empresa_id


def _empresa_de_form(empresa_id: int = Form(...)) -> int:
    return empresa_id


ejecutar_conciliacion = requiere(
    "conciliacion.ejecutar", empresa_de=_empresa_de_form
)
ver_conciliacion = requiere("conciliacion.ver", empresa_de=_empresa_de_query)


@router.post("/conciliar", status_code=201)
def conciliar_wiilog(
    empresa_id: int = Form(...),
    acceso: Acceso = Depends(ejecutar_conciliacion),
    periodo_id: int = Form(...),
    fuente_ordenes_id: int = Form(...),
    fuente_wallet_id: int = Form(...),
    ordenes: UploadFile = File(...),
    wallet: UploadFile = File(...),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    ordenes_contenido = ordenes.file.read()
    wallet_contenido = wallet.file.read()

    try:
        ejecucion = ejecutar_y_persistir_wiilog(
            session,
            empresa_id=empresa_id,
            periodo_id=periodo_id,
            fuente_ordenes_id=fuente_ordenes_id,
            fuente_wallet_id=fuente_wallet_id,
            ordenes_contenido=ordenes_contenido,
            wallet_contenido=wallet_contenido,
            usuario_id=acceso.usuario.id,
        )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                "Uno de estos archivos ya fue cargado para la empresa. "
                "Usa una exportación nueva o consulta la conciliación existente."
            ),
        ) from exc
    except ConfiguracionWiilogFaltanteError as exc:
        session.rollback()
        raise HTTPException(
            status_code=503,
            detail=MENSAJE_CONFIGURACION_FALTANTE,
        ) from exc
    except ContextoCargaInvalidoError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PeriodoCerradoError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
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
            "ordenes_id": ejecucion.carga_ordenes_id,
            "wallet_id": ejecucion.carga_wallet_id,
        },
        "hallazgos_creados": ejecucion.hallazgos_creados,
        "hallazgos_por_gravedad": ejecucion.hallazgos_por_gravedad,
        "sincronizacion": ejecucion.sincronizacion,
        "resumen": ejecucion.resumen,
    }


@router.get("/hallazgos")
def consultar_hallazgos_wiilog(
    empresa_id: int,
    periodo_id: int,
    todas_las_cargas: bool = False,
    _acceso: Acceso = Depends(ver_conciliacion),
    session: Session = Depends(obtener_session),
) -> list[dict[str, object]]:
    try:
        hallazgos = listar_hallazgos_wiilog(
            session,
            empresa_id=empresa_id,
            periodo_id=periodo_id,
            todas_las_cargas=todas_las_cargas,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return [hallazgo_json(hallazgo) for hallazgo in hallazgos]
