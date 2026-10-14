"""Expedientes de corrección; no afectan movimientos ni saldos."""
from decimal import Decimal
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Integer, Numeric, String, Text, UniqueConstraint, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from app.core.db import Base
from app.core.cargas import Carga
from app.core.periodos import Periodo
from app.core.auditoria import registrar_auditoria
from .ejecucion_reapertura import EjecucionReapertura

class ExpedienteCorreccion(Base):
    __tablename__ = "wallets_expedientes_correccion"
    __table_args__ = (
        ForeignKeyConstraint(["periodo_id","empresa_id"],["periodos.id","periodos.empresa_id"],name="fk_wallets_expediente_periodo_empresa",ondelete="RESTRICT"),
        UniqueConstraint("ejecucion_id","carga_id","movimiento_ref",name="uq_wallets_expediente_movimiento"),
    )
    id: Mapped[int] = mapped_column(Integer,primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"),nullable=False)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodos.id"),nullable=False)
    ejecucion_id: Mapped[int] = mapped_column(ForeignKey("wallets_ejecuciones_reapertura.id"),nullable=False)
    carga_id: Mapped[int] = mapped_column(ForeignKey("cargas.id"),nullable=False)
    movimiento_ref: Mapped[str] = mapped_column(String(320),nullable=False)
    valor_anterior: Mapped[Decimal] = mapped_column(Numeric(20,2),nullable=False)
    valor_propuesto: Mapped[Decimal] = mapped_column(Numeric(20,2),nullable=False)
    evidencia_antes_ref: Mapped[str] = mapped_column(String(512),nullable=False)
    evidencia_despues_ref: Mapped[str] = mapped_column(String(512),nullable=False)
    justificacion: Mapped[str] = mapped_column(Text,nullable=False)
    preparado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"),nullable=False)
    preparado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False,server_default=func.now())
    decision: Mapped[str | None] = mapped_column(String(24))
    decidido_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    decidido_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_decision: Mapped[str | None] = mapped_column(Text)

def preparar(session:Session,*,empresa_id:int,periodo_id:int,ejecucion_id:int,carga_id:int,
            movimiento_ref:str,valor_anterior:Decimal,valor_propuesto:Decimal,
            evidencia_antes_ref:str,evidencia_despues_ref:str,justificacion:str,
            usuario_id:int)->ExpedienteCorreccion:
    periodo=session.scalar(select(Periodo).where(Periodo.id==periodo_id,Periodo.empresa_id==empresa_id).with_for_update())
    if periodo is None:
        raise LookupError("Período no encontrado para la empresa.")
    if periodo.cerrado:
        raise ValueError("No se documenta corrección nueva sobre período cerrado.")
    ejecucion=session.scalar(select(EjecucionReapertura).where(EjecucionReapertura.id==ejecucion_id,
        EjecucionReapertura.periodo_id==periodo_id,EjecucionReapertura.empresa_id==empresa_id))
    carga=session.scalar(select(Carga).where(Carga.id==carga_id,Carga.periodo_id==periodo_id,Carga.empresa_id==empresa_id))
    if ejecucion is None or carga is None:
        raise LookupError("Ejecución o carga original inexistente en este período/empresa.")
    referencias=(movimiento_ref.strip(),evidencia_antes_ref.strip(),evidencia_despues_ref.strip(),justificacion.strip())
    if any(not x for x in referencias) or len(referencias[0])>320 or max(len(referencias[1]),len(referencias[2]))>512:
        raise ValueError("Movimiento, justificación y evidencias antes/después son obligatorios.")
    if not all(v.is_finite() and v.as_tuple().exponent>=-2 for v in (valor_anterior,valor_propuesto)):
        raise ValueError("Valores monetarios deben ser finitos y tener máximo 2 decimales.")
    if valor_anterior==valor_propuesto:
        raise ValueError("Sin diferencia entre valores: no corresponde corrección.")
    if session.scalar(select(ExpedienteCorreccion.id).where(
        ExpedienteCorreccion.ejecucion_id==ejecucion_id,ExpedienteCorreccion.carga_id==carga_id,
        ExpedienteCorreccion.movimiento_ref==referencias[0])) is not None:
        raise ValueError("El expediente del movimiento ya existe.")
    fila=ExpedienteCorreccion(empresa_id=empresa_id,periodo_id=periodo_id,ejecucion_id=ejecucion_id,
        carga_id=carga_id,movimiento_ref=referencias[0],valor_anterior=valor_anterior,
        valor_propuesto=valor_propuesto,evidencia_antes_ref=referencias[1],evidencia_despues_ref=referencias[2],
        justificacion=referencias[3],preparado_por=usuario_id)
    session.add(fila)
    session.flush()
    registrar_auditoria(session,usuario_id=usuario_id,accion="WALLET_CORRECCION_PREPARAR",
        entidad="wallets_expedientes_correccion",entidad_id=fila.id,empresa_id=empresa_id,
        antes={"valor":str(valor_anterior)},despues={"valor_propuesto":str(valor_propuesto),
        "carga_id":carga_id,"movimiento_ref":referencias[0],"evidencia_antes_ref":referencias[1],
        "evidencia_despues_ref":referencias[2],"justificacion":referencias[3]})
    return fila

def decidir(session:Session,*,empresa_id:int,periodo_id:int,expediente_id:int,
           usuario_id:int,decision:str,motivo:str)->ExpedienteCorreccion:
    periodo=session.scalar(select(Periodo).where(Periodo.id==periodo_id,Periodo.empresa_id==empresa_id).with_for_update())
    if periodo is None:
        raise LookupError("Período no encontrado.")
    if periodo.cerrado:
        raise ValueError("Período cerrado: no se permite decidir correcciones.")
    fila=session.scalar(select(ExpedienteCorreccion).where(
        ExpedienteCorreccion.id==expediente_id,ExpedienteCorreccion.empresa_id==empresa_id,
        ExpedienteCorreccion.periodo_id==periodo_id).with_for_update())
    if fila is None:
        raise LookupError("Expediente no encontrado.")
    if fila.decision is not None:
        raise ValueError("Expediente ya decidido.")
    if fila.preparado_por==usuario_id:
        raise ValueError("No se puede aprobar una corrección propia.")
    if decision not in {"AUTORIZAR_EJECUCION","RECHAZAR"} or not motivo.strip():
        raise ValueError("Decisión y justificación obligatorias.")
    fila.decision=decision
    fila.decidido_por=usuario_id
    fila.decidido_at=datetime.now(__import__("datetime").timezone.utc)
    fila.motivo_decision=motivo.strip()
    registrar_auditoria(session,usuario_id=usuario_id,accion="WALLET_CORRECCION_DECIDIR",
        entidad="wallets_expedientes_correccion",entidad_id=fila.id,empresa_id=empresa_id,
        antes={"decision":None},despues={"decision":decision,"motivo":fila.motivo_decision,
        "aplicada":False})
    return fila
