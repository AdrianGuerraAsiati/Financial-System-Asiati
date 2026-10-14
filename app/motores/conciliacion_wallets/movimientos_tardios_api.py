"""Consulta y detección auditada de incidencias de corte."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth.dependencias import Acceso, requiere
from app.core.session import obtener_session
from .movimientos_tardios import registrar, listar

router = APIRouter(prefix="/wallets/periodos", tags=["wallets"])

def _empresa(empresa_id: int) -> int:
    return empresa_id

ver = requiere("conciliacion.ver", empresa_de=_empresa)
registrar_permiso = requiere("conciliacion.ejecutar", empresa_de=_empresa)


class IncidenciaEntrada(BaseModel):
    tipo_wallet: str
    identidad_wallet: str | None = None
    identificador_externo: str = Field(min_length=1, max_length=320)
    instante_movimiento: datetime
    instante_recepcion: datetime
    evidencia_ref: str = Field(min_length=1, max_length=512)


@router.get("/{periodo_id}/movimientos-tardios")
def consultar(empresa_id: int, periodo_id: int, _acceso: Acceso = Depends(ver),
              session: Session = Depends(obtener_session)) -> list[dict]:
    try:
        items = listar(session, empresa_id=empresa_id, periodo_id=periodo_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [{"id": i.id, "tipo_wallet": i.tipo_wallet, "identidad_wallet": i.identidad_wallet,
             "identificador_externo": i.identificador_externo, "clasificacion": i.clasificacion,
             "instante_movimiento": i.instante_movimiento, "instante_recepcion": i.instante_recepcion,
             "evidencia_ref": i.evidencia_ref, "registrado_por": i.registrado_por}
            for i in items]


@router.post("/{periodo_id}/movimientos-tardios", status_code=201)
def detectar(empresa_id: int, periodo_id: int, datos: IncidenciaEntrada,
             acceso: Acceso = Depends(registrar_permiso),
             session: Session = Depends(obtener_session)) -> dict:
    try:
        item = registrar(session, empresa_id=empresa_id, periodo_id=periodo_id,
                        usuario_id=acceso.usuario.id, tipo_wallet=datos.tipo_wallet,
                        identidad_wallet=datos.identidad_wallet,
                        identificador_externo=datos.identificador_externo,
                        instante_movimiento=datos.instante_movimiento,
                        instante_recepcion=datos.instante_recepcion,
                        evidencia_ref=datos.evidencia_ref, ip=acceso.ip)
        session.commit()
        return {"id": item.id, "clasificacion": item.clasificacion}
    except LookupError as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Incidencia duplicada o inconsistente.") from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        session.rollback()
        raise
