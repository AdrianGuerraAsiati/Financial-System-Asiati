"""Consulta y declaración auditada de corte; no habilita cierre."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth.dependencias import Acceso, requiere
from app.core.session import obtener_session
from .corte_operativo import configurar_corte, consultar_corte

router = APIRouter(prefix="/wallets/periodos", tags=["wallets"])

def _empresa(empresa_id: int) -> int:
    return empresa_id

ver = requiere("conciliacion.ver", empresa_de=_empresa)
configurar = requiere("periodos.cerrar", empresa_de=_empresa)

class CorteEntrada(BaseModel):
    zona_horaria: str = Field(min_length=1, max_length=100)
    corte_local: datetime
    motivo: str = Field(min_length=1, max_length=2000)

@router.get("/{periodo_id}/corte-operativo")
def ver_corte(empresa_id: int, periodo_id: int,
              _acceso: Acceso = Depends(ver),
              session: Session = Depends(obtener_session)) -> dict:
    try:
        corte = consultar_corte(session, empresa_id=empresa_id, periodo_id=periodo_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if corte is None:
        return {"configurado": False, "empresa_id": empresa_id, "periodo_id": periodo_id}
    return {"configurado": True, "empresa_id": empresa_id, "periodo_id": periodo_id,
            "zona_horaria": corte.zona_horaria, "corte_local": corte.corte_local,
            "corte_utc": corte.corte_utc, "registrado_por": corte.registrado_por}

@router.post("/{periodo_id}/corte-operativo", status_code=201)
def declarar_corte(empresa_id: int, periodo_id: int, datos: CorteEntrada,
                   acceso: Acceso = Depends(configurar),
                   session: Session = Depends(obtener_session)) -> dict:
    try:
        corte = configurar_corte(
            session, empresa_id=empresa_id, periodo_id=periodo_id,
            usuario_id=acceso.usuario.id, zona_horaria=datos.zona_horaria,
            corte_local=datos.corte_local, motivo=datos.motivo, ip=acceso.ip,
        )
        session.commit()
        return {"id": corte.id, "configurado": True}
    except LookupError as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="El corte ya existe.") from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        session.rollback()
        raise
