from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth.dependencias import Acceso, requiere
from app.core.session import obtener_session
from app.core.supervision.consultas import (
    acciones_por_usuario,
    estado_conciliaciones,
    ultimos_ingresos,
)


router = APIRouter(prefix="/supervision", tags=["supervision"])

supervisar = requiere("supervision.ver")


@router.get("/conciliaciones")
def conciliaciones(
    empresa_id: int | None = None,
    acceso: Acceso = Depends(supervisar),
    session: Session = Depends(obtener_session),
) -> list[dict[str, object]]:
    return estado_conciliaciones(
        session,
        empresas_visibles=acceso.empresas_visibles,
        empresa_id=empresa_id,
    )


@router.get("/ingresos")
def ingresos(
    acceso: Acceso = Depends(supervisar),
    session: Session = Depends(obtener_session),
) -> list[dict[str, object]]:
    return ultimos_ingresos(session, empresas_visibles=acceso.empresas_visibles)


@router.get("/acciones")
def acciones(
    usuario_id: int | None = None,
    empresa_id: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    acceso: Acceso = Depends(supervisar),
    session: Session = Depends(obtener_session),
) -> list[dict[str, object]]:
    return acciones_por_usuario(
        session,
        empresas_visibles=acceso.empresas_visibles,
        usuario_id=usuario_id,
        empresa_id=empresa_id,
        desde=desde,
        hasta=hasta,
    )
