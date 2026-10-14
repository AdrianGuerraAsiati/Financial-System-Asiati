"""Solicitudes auditadas; una aprobación NO ejecuta reapertura financiera."""
from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from app.core.db import Base
from app.core.periodos import Periodo
from app.core.auditoria import registrar_auditoria
from .revision_tardios import RevisionTardio
from .movimientos_tardios import MovimientoTardio

class SolicitudReapertura(Base):
    __tablename__ = "wallets_solicitudes_reapertura"
    __table_args__ = (
        ForeignKeyConstraint(["periodo_id","empresa_id"],["periodos.id","periodos.empresa_id"],name="fk_wallets_solicitud_periodo_empresa",ondelete="RESTRICT"),
        UniqueConstraint("revision_id",name="uq_wallets_solicitud_revision"),
        CheckConstraint("decision IS NULL OR decision IN ('APROBADA','RECHAZADA')",name="ck_wallets_solicitud_decision"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"),nullable=False)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodos.id"),nullable=False)
    revision_id: Mapped[int] = mapped_column(ForeignKey("wallets_tardios_revisiones.id"),nullable=False)
    solicitado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"),nullable=False)
    solicitado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)
    motivo: Mapped[str] = mapped_column(Text,nullable=False)
    evidencia_ref: Mapped[str] = mapped_column(String(512),nullable=False)
    decision: Mapped[str | None] = mapped_column(String(16))
    decidido_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    decidido_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_decision: Mapped[str | None] = mapped_column(Text)

def solicitar(session: Session, *, empresa_id: int, periodo_id: int, revision_id: int, usuario_id: int, motivo: str, evidencia_ref: str):
    periodo = session.scalar(select(Periodo).where(Periodo.id==periodo_id,Periodo.empresa_id==empresa_id).with_for_update())
    if periodo is None:
        raise LookupError("Período no encontrado.")
    if not periodo.cerrado:
        raise ValueError("Se requiere un período cerrado.")
    revision = session.scalar(select(RevisionTardio).join(MovimientoTardio,RevisionTardio.movimiento_id==MovimientoTardio.id).where(RevisionTardio.id==revision_id,MovimientoTardio.empresa_id==empresa_id,MovimientoTardio.periodo_id==periodo_id))
    if revision is None:
        raise LookupError("Revisión no encontrada.")
    if revision.conclusion!="REQUIERE_CORRECCION" or revision.decision!="AUTORIZAR_GESTION":
        raise ValueError("Se requiere revisión y autorización de gestión.")
    if revision.autorizado_por!=usuario_id:
        raise ValueError("Solo el autorizador financiero de la gestión puede solicitar.")
    if not motivo.strip() or not evidencia_ref.strip() or len(evidencia_ref.strip())>512:
        raise ValueError("Motivo y evidencia obligatorios.")
    if session.scalar(select(SolicitudReapertura.id).where(SolicitudReapertura.revision_id==revision_id)) is not None:
        raise ValueError("Solicitud duplicada.")
    fila=SolicitudReapertura(empresa_id=empresa_id,periodo_id=periodo_id,revision_id=revision_id,solicitado_por=usuario_id,motivo=motivo.strip(),evidencia_ref=evidencia_ref.strip())
    session.add(fila)
    session.flush()
    registrar_auditoria(session,usuario_id=usuario_id,accion="WALLET_REAPERTURA_SOLICITAR",entidad="wallets_solicitudes_reapertura",entidad_id=fila.id,empresa_id=empresa_id,despues={"revision_id":revision_id,"periodo_id":periodo_id,"motivo":fila.motivo,"evidencia_ref":fila.evidencia_ref})
    return fila

def decidir(session: Session, *, empresa_id: int, periodo_id: int, solicitud_id: int, usuario_id: int, decision: str, motivo: str):
    periodo=session.scalar(select(Periodo).where(Periodo.id==periodo_id,Periodo.empresa_id==empresa_id).with_for_update())
    if periodo is None:
        raise LookupError("Período no encontrado.")
    fila=session.scalar(select(SolicitudReapertura).where(SolicitudReapertura.id==solicitud_id,SolicitudReapertura.empresa_id==empresa_id,SolicitudReapertura.periodo_id==periodo_id).with_for_update())
    if fila is None:
        raise LookupError("Solicitud no encontrada.")
    if fila.decision is not None:
        raise ValueError("Solicitud ya decidida.")
    if fila.solicitado_por==usuario_id:
        raise ValueError("No puede decidir su propia solicitud.")
    if decision not in ("APROBADA","RECHAZADA") or not motivo.strip():
        raise ValueError("Decisión y motivo obligatorios.")
    if decision=="APROBADA" and not periodo.cerrado:
        raise ValueError("El período ya está abierto.")
    fila.decision=decision
    fila.decidido_por=usuario_id
    fila.decidido_at=datetime.now(timezone.utc)
    fila.motivo_decision=motivo.strip()
    registrar_auditoria(session,usuario_id=usuario_id,accion="WALLET_REAPERTURA_DECIDIR",entidad="wallets_solicitudes_reapertura",entidad_id=fila.id,empresa_id=empresa_id,antes={"decision":None},despues={"decision":decision,"motivo":fila.motivo_decision,"periodo_id":periodo_id,"reapertura_ejecutada":False})
    return fila
