"""Preparación y decisión de expedientes de corrección sin aplicación contable."""
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth.dependencias import Acceso, requiere
from app.core.periodos import Periodo
from app.core.session import obtener_session
from .expedientes_correccion import ExpedienteCorreccion, preparar, decidir

router = APIRouter(prefix="/wallets/periodos", tags=["wallets"])

def _empresa(empresa_id: int) -> int:
    return empresa_id

ver_permiso = requiere("conciliacion.ver", empresa_de=_empresa)
preparar_permiso = requiere("conciliacion.ejecutar", empresa_de=_empresa)
decidir_permiso = requiere("periodos.cerrar", empresa_de=_empresa)

class PrepararDatos(BaseModel):
    ejecucion_id: int
    carga_id: int
    movimiento_ref: str = Field(min_length=1, max_length=320)
    valor_anterior: Decimal
    valor_propuesto: Decimal
    evidencia_antes_ref: str = Field(min_length=1, max_length=512)
    evidencia_despues_ref: str = Field(min_length=1, max_length=512)
    justificacion: str = Field(min_length=1, max_length=2000)

class DecisionDatos(BaseModel):
    decision: str
    motivo: str = Field(min_length=1, max_length=2000)

def _hacer(session, operacion):
    try:
        fila = operacion()
        session.commit()
        return {"id": fila.id, "decision": fila.decision, "aplicada": False}
    except LookupError as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Expediente duplicado o inconsistente.") from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        session.rollback()
        raise

@router.post("/{periodo_id}/expedientes-correccion", status_code=201)
def crear_expediente(empresa_id: int, periodo_id: int, datos: PrepararDatos,
                    acceso: Acceso = Depends(preparar_permiso),
                    session: Session = Depends(obtener_session)) -> dict:
    return _hacer(session, lambda: preparar(
        session, empresa_id=empresa_id, periodo_id=periodo_id,
        ejecucion_id=datos.ejecucion_id, carga_id=datos.carga_id,
        movimiento_ref=datos.movimiento_ref, valor_anterior=datos.valor_anterior,
        valor_propuesto=datos.valor_propuesto,
        evidencia_antes_ref=datos.evidencia_antes_ref,
        evidencia_despues_ref=datos.evidencia_despues_ref,
        justificacion=datos.justificacion, usuario_id=acceso.usuario.id))

@router.post("/{periodo_id}/expedientes-correccion/{expediente_id}/decidir")
def decidir_expediente(empresa_id: int, periodo_id: int, expediente_id: int,
                      datos: DecisionDatos, acceso: Acceso = Depends(decidir_permiso),
                      session: Session = Depends(obtener_session)) -> dict:
    return _hacer(session, lambda: decidir(
        session, empresa_id=empresa_id, periodo_id=periodo_id,
        expediente_id=expediente_id, usuario_id=acceso.usuario.id,
        decision=datos.decision, motivo=datos.motivo))

@router.get("/{periodo_id}/expedientes-correccion")
def consultar_expedientes(empresa_id: int, periodo_id: int,
                         _acceso: Acceso = Depends(ver_permiso),
                         session: Session = Depends(obtener_session)) -> list[dict]:
    periodo = session.get(Periodo, periodo_id)
    if periodo is None or periodo.empresa_id != empresa_id:
        raise HTTPException(status_code=404, detail="Período no encontrado.")
    filas = session.scalars(select(ExpedienteCorreccion).where(
        ExpedienteCorreccion.empresa_id == empresa_id,
        ExpedienteCorreccion.periodo_id == periodo_id).order_by(ExpedienteCorreccion.id))
    return [{"id": f.id, "ejecucion_id": f.ejecucion_id, "carga_id": f.carga_id,
             "movimiento_ref": f.movimiento_ref, "valor_anterior": str(f.valor_anterior),
             "valor_propuesto": str(f.valor_propuesto),
             "evidencia_antes_ref": f.evidencia_antes_ref,
             "evidencia_despues_ref": f.evidencia_despues_ref,
             "justificacion": f.justificacion, "preparado_por": f.preparado_por,
             "decision": f.decision, "decidido_por": f.decidido_por,
             "motivo_decision": f.motivo_decision, "aplicada": False} for f in filas]
