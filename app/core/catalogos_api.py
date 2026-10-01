from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.dependencias import Acceso, requiere
from app.core.empresas import Empresa
from app.core.fuentes import Fuente
from app.core.periodos import Periodo
from app.core.session import obtener_session


router = APIRouter(tags=["catalogos"])


def _empresa_de_query(empresa_id: int) -> int:
    return empresa_id


ver_catalogos = requiere("conciliacion.ver", empresa_de=_empresa_de_query)


def _asegurar_empresa(session: Session, empresa_id: int) -> None:
    if session.get(Empresa, empresa_id) is None:
        raise HTTPException(
            status_code=404,
            detail="No encontramos esa empresa. Revisa el selector e inténtalo de nuevo.",
        )


@router.get("/periodos")
def listar_periodos(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_catalogos),
    session: Session = Depends(obtener_session),
) -> list[dict[str, object]]:
    _asegurar_empresa(session, empresa_id)
    periodos = session.scalars(
        select(Periodo)
        .where(Periodo.empresa_id == empresa_id)
        .order_by(Periodo.fecha_inicio.desc(), Periodo.id.desc())
    )
    return [
        {
            "id": periodo.id,
            "empresa_id": periodo.empresa_id,
            "fecha_inicio": periodo.fecha_inicio.isoformat(),
            "fecha_fin": periodo.fecha_fin.isoformat(),
            "cerrado": periodo.cerrado,
        }
        for periodo in periodos
    ]


@router.get("/fuentes")
def listar_fuentes(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_catalogos),
    session: Session = Depends(obtener_session),
) -> list[dict[str, object]]:
    _asegurar_empresa(session, empresa_id)
    fuentes = session.scalars(
        select(Fuente)
        .where(Fuente.empresa_id == empresa_id)
        .order_by(Fuente.nombre, Fuente.id)
    )
    return [
        {
            "id": fuente.id,
            "empresa_id": fuente.empresa_id,
            "nombre": fuente.nombre,
        }
        for fuente in fuentes
    ]
