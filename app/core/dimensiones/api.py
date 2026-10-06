from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth.dependencias import Acceso, requiere
from app.core.dimensiones.model import DimensionValor
from app.core.dimensiones.service import (
    DimensionDuplicadaError,
    DimensionError,
    actualizar_valor,
    crear_valor,
    listar_valores,
)
from app.core.session import obtener_session


router = APIRouter(prefix="/dimensiones", tags=["dimensiones"])


class CrearEntrada(BaseModel):
    dimension: str
    valor: str


class ActualizarEntrada(BaseModel):
    valor: str | None = None
    activo: bool | None = None


def _json(valor: DimensionValor) -> dict[str, object]:
    return {"id": valor.id, "dimension": valor.dimension, "valor": valor.valor, "activo": valor.activo}


def _ejecutar(session: Session, accion) -> DimensionValor:
    try:
        valor = accion()
        session.commit()
    except DimensionDuplicadaError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DimensionError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return valor


@router.get("")
def consultar(
    dimension: str | None = None,
    incluir_inactivos: bool = False,
    _acceso: Acceso = Depends(requiere("parametros.ver")),
    session: Session = Depends(obtener_session),
) -> list[dict[str, object]]:
    try:
        valores = listar_valores(session, dimension=dimension, incluir_inactivos=incluir_inactivos)
    except DimensionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return [_json(v) for v in valores]


@router.post("", status_code=201)
def crear(
    datos: CrearEntrada,
    acceso: Acceso = Depends(requiere("dimensiones.gestionar")),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    valor = _ejecutar(
        session,
        lambda: crear_valor(
            session, dimension=datos.dimension, valor=datos.valor, usuario_id=acceso.usuario.id, ip=acceso.ip
        ),
    )
    return _json(valor)


@router.patch("/{valor_id}")
def actualizar(
    valor_id: int,
    datos: ActualizarEntrada,
    acceso: Acceso = Depends(requiere("dimensiones.gestionar")),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    valor = session.get(DimensionValor, valor_id)
    if valor is None:
        raise HTTPException(status_code=404, detail="El valor no existe. Recarga la lista.")
    actualizado = _ejecutar(
        session,
        lambda: actualizar_valor(
            session,
            valor,
            nuevo_valor=datos.valor,
            activo=datos.activo,
            usuario_id=acceso.usuario.id,
            ip=acceso.ip,
        ),
    )
    return _json(actualizado)
