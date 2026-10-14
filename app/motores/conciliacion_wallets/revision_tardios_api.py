"""Revisión de incidencias sin autorización automática de reapertura o asiento."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth.dependencias import Acceso, requiere
from app.core.session import obtener_session
from .revision_tardios import revisar, decidir, listar_revisiones
from .movimientos_tardios import listar as listar_movimientos

router = APIRouter(prefix="/wallets/periodos", tags=["wallets"])

def _empresa(empresa_id: int) -> int:
    return empresa_id

ver = requiere("conciliacion.ver", empresa_de=_empresa)
revisar_permiso = requiere("conciliacion.ejecutar", empresa_de=_empresa)
decidir_permiso = requiere("periodos.cerrar", empresa_de=_empresa)


class RevisionEntrada(BaseModel):
    conclusion: str
    justificacion: str = Field(min_length=1, max_length=2000)
    evidencia_revision: str = Field(min_length=1, max_length=512)


class DecisionEntrada(BaseModel):
    decision: str
    justificacion: str = Field(min_length=1, max_length=2000)


def _aplicar(session, operacion):
    try:
        fila = operacion()
        session.commit()
        return {"id": fila.id, "movimiento_id": fila.movimiento_id,
                "conclusion": fila.conclusion, "decision": fila.decision}
    except LookupError as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Revisión duplicada o inconsistente.") from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        session.rollback()
        raise


@router.get("/{periodo_id}/revisiones-tardios")
def consultar(empresa_id: int, periodo_id: int, _acceso: Acceso = Depends(ver),
              session: Session = Depends(obtener_session)) -> list[dict]:
    try:
        listar_movimientos(session, empresa_id=empresa_id, periodo_id=periodo_id)
        filas = listar_revisiones(session, empresa_id=empresa_id, periodo_id=periodo_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [{"id": f.id, "movimiento_id": f.movimiento_id, "conclusion": f.conclusion,
             "justificacion": f.justificacion, "evidencia_revision": f.evidencia_revision,
             "revisado_por": f.revisado_por, "decision": f.decision,
             "justificacion_decision": f.justificacion_decision, "autorizado_por": f.autorizado_por}
            for f in filas]


@router.post("/{periodo_id}/movimientos-tardios/{movimiento_id}/revisar", status_code=201)
def revisar_incidencia(empresa_id: int, periodo_id: int, movimiento_id: int,
                      datos: RevisionEntrada, acceso: Acceso = Depends(revisar_permiso),
                      session: Session = Depends(obtener_session)) -> dict:
    return _aplicar(session, lambda: revisar(session, empresa_id=empresa_id,
        periodo_id=periodo_id, movimiento_id=movimiento_id, usuario_id=acceso.usuario.id,
        conclusion=datos.conclusion, justificacion=datos.justificacion,
        evidencia_revision=datos.evidencia_revision, ip=acceso.ip))


@router.post("/{periodo_id}/movimientos-tardios/{movimiento_id}/decidir", status_code=200)
def decidir_incidencia(empresa_id: int, periodo_id: int, movimiento_id: int,
                      datos: DecisionEntrada, acceso: Acceso = Depends(decidir_permiso),
                      session: Session = Depends(obtener_session)) -> dict:
    return _aplicar(session, lambda: decidir(session, empresa_id=empresa_id,
        periodo_id=periodo_id, movimiento_id=movimiento_id, usuario_id=acceso.usuario.id,
        decision=datos.decision, justificacion=datos.justificacion, ip=acceso.ip))
