"""Solicitud de reapertura y decisión de Superadministración sin ejecutar reapertura."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.auth.dependencias import Acceso, requiere
from app.core.session import obtener_session
from .solicitudes_reapertura import solicitar, decidir, SolicitudReapertura
from .ejecucion_reapertura import ejecutar
from sqlalchemy import select
from app.core.periodos import Periodo

router=APIRouter(prefix="/wallets/periodos",tags=["wallets"])
def _empresa(empresa_id: int)->int:
    return empresa_id
solicitar_permiso=requiere("periodos.cerrar",empresa_de=_empresa)
decidir_permiso=requiere("periodos.reabrir",empresa_de=_empresa)
ver=requiere("conciliacion.ver",empresa_de=_empresa)

class SolicitudDatos(BaseModel):
    revision_id: int
    motivo: str=Field(min_length=1,max_length=2000)
    evidencia_ref: str=Field(min_length=1,max_length=512)

class DecisionDatos(BaseModel):
    decision: str
    motivo: str=Field(min_length=1,max_length=2000)

def _ejecutar(session,accion):
    try:
        fila=accion()
        session.commit()
        return {"id":fila.id,"decision":fila.decision,"reapertura_ejecutada":False}
    except LookupError as exc:
        session.rollback()
        raise HTTPException(status_code=404,detail=str(exc)) from exc
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409,detail="Solicitud duplicada o inconsistente.") from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422,detail=str(exc)) from exc
    except Exception:
        session.rollback()
        raise

@router.post("/{periodo_id}/solicitudes-reapertura",status_code=201)
def solicitar_reapertura(empresa_id:int,periodo_id:int,datos:SolicitudDatos,acceso:Acceso=Depends(solicitar_permiso),session:Session=Depends(obtener_session))->dict:
    return _ejecutar(session,lambda:solicitar(session,empresa_id=empresa_id,periodo_id=periodo_id,revision_id=datos.revision_id,usuario_id=acceso.usuario.id,motivo=datos.motivo,evidencia_ref=datos.evidencia_ref))

@router.post("/{periodo_id}/solicitudes-reapertura/{solicitud_id}/decidir")
def decidir_reapertura(empresa_id:int,periodo_id:int,solicitud_id:int,datos:DecisionDatos,acceso:Acceso=Depends(decidir_permiso),session:Session=Depends(obtener_session))->dict:
    return _ejecutar(session,lambda:decidir(session,empresa_id=empresa_id,periodo_id=periodo_id,solicitud_id=solicitud_id,usuario_id=acceso.usuario.id,decision=datos.decision,motivo=datos.motivo))

@router.get("/{periodo_id}/solicitudes-reapertura")
def consultar_solicitudes(empresa_id:int,periodo_id:int,_acceso:Acceso=Depends(ver),session:Session=Depends(obtener_session))->list[dict]:
    periodo=session.get(Periodo,periodo_id)
    if periodo is None or periodo.empresa_id!=empresa_id:
        raise HTTPException(status_code=404,detail="Período no encontrado.")
    filas=session.scalars(select(SolicitudReapertura).where(SolicitudReapertura.empresa_id==empresa_id,SolicitudReapertura.periodo_id==periodo_id).order_by(SolicitudReapertura.id))
    return [{"id":x.id,"revision_id":x.revision_id,"solicitado_por":x.solicitado_por,"motivo":x.motivo,"evidencia_ref":x.evidencia_ref,"decision":x.decision,"decidido_por":x.decidido_por,"motivo_decision":x.motivo_decision} for x in filas]

class EjecutarReaperturaDatos(BaseModel):
    motivo: str=Field(min_length=1,max_length=2000)
    plan_ref: str=Field(min_length=1,max_length=512)
    evidencia_previa_ref: str=Field(min_length=1,max_length=512)

@router.post("/{periodo_id}/solicitudes-reapertura/{solicitud_id}/ejecutar")
def ejecutar_reapertura(empresa_id:int, periodo_id:int, solicitud_id:int,
                        datos:EjecutarReaperturaDatos,
                        acceso:Acceso=Depends(decidir_permiso),
                        session:Session=Depends(obtener_session))->dict:
    try:
        registro=ejecutar(session,empresa_id=empresa_id,periodo_id=periodo_id,
            solicitud_id=solicitud_id,usuario_id=acceso.usuario.id,
            motivo=datos.motivo,plan_ref=datos.plan_ref,
            evidencia_previa_ref=datos.evidencia_previa_ref,ip=acceso.ip)
        session.commit()
        return {"ejecucion_id":registro.id,"solicitud_id":solicitud_id,
                "reapertura_ejecutada":True,"correccion_ejecutada":False}
    except LookupError as exc:
        session.rollback()
        raise HTTPException(status_code=404,detail=str(exc)) from exc
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409,detail="Ejecución duplicada o inconsistente.") from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422,detail=str(exc)) from exc
    except Exception:
        session.rollback()
        raise
