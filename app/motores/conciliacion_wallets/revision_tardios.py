"""Segregación de revisión técnica y decisión financiera sin aplicar correcciones."""
from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.auditoria import registrar_auditoria
from app.core.db import Base
from .movimientos_tardios import MovimientoTardio


class RevisionTardio(Base):
    __tablename__ = "wallets_tardios_revisiones"
    __table_args__ = (
        UniqueConstraint("movimiento_id", name="uq_wallets_tardios_revision_movimiento"),
        CheckConstraint("conclusion IN ('REQUIERE_CORRECCION','SIN_IMPACTO')", name="ck_wallets_tardios_conclusion"),
        CheckConstraint("decision IS NULL OR decision IN ('AUTORIZAR_GESTION','RECHAZAR_GESTION')", name="ck_wallets_tardios_decision"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    movimiento_id: Mapped[int] = mapped_column(ForeignKey("wallets_movimientos_tardios.id", ondelete="RESTRICT"), nullable=False)
    revisado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    revisado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    conclusion: Mapped[str] = mapped_column(String(32), nullable=False)
    justificacion: Mapped[str] = mapped_column(Text, nullable=False)
    evidencia_revision: Mapped[str] = mapped_column(String(512), nullable=False)
    autorizado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True)
    autorizado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    justificacion_decision: Mapped[str | None] = mapped_column(Text, nullable=True)


def _movimiento(session: Session, empresa_id: int, periodo_id: int, movimiento_id: int) -> MovimientoTardio:
    item = session.scalar(select(MovimientoTardio).where(
        MovimientoTardio.id == movimiento_id, MovimientoTardio.empresa_id == empresa_id,
        MovimientoTardio.periodo_id == periodo_id,
    ))
    if item is None:
        raise LookupError("Incidencia no encontrada para la empresa y período.")
    return item


def revisar(session: Session, *, empresa_id: int, periodo_id: int, movimiento_id: int,
            usuario_id: int, conclusion: str, justificacion: str,
            evidencia_revision: str, ip: str | None = None) -> RevisionTardio:
    movimiento = _movimiento(session, empresa_id, periodo_id, movimiento_id)
    if conclusion not in {"REQUIERE_CORRECCION", "SIN_IMPACTO"}:
        raise ValueError("Conclusión de revisión inválida.")
    if not justificacion.strip() or not evidencia_revision.strip():
        raise ValueError("Revisión requiere justificación y referencia de evidencia.")
    if session.scalar(select(RevisionTardio.id).where(RevisionTardio.movimiento_id == movimiento_id)) is not None:
        raise ValueError("Incidencia ya revisada.")
    fila = RevisionTardio(movimiento_id=movimiento.id, revisado_por=usuario_id,
        conclusion=conclusion, justificacion=justificacion.strip(),
        evidencia_revision=evidencia_revision.strip())
    session.add(fila)
    session.flush()
    registrar_auditoria(session, usuario_id=usuario_id, accion="WALLET_TARDIO_REVISAR",
        entidad="wallets_tardios_revisiones", entidad_id=fila.id, empresa_id=empresa_id,
        despues={"movimiento_id": movimiento_id, "periodo_id": periodo_id,
                 "conclusion": conclusion, "justificacion": fila.justificacion,
                 "evidencia_revision": fila.evidencia_revision}, ip=ip)
    return fila


def decidir(session: Session, *, empresa_id: int, periodo_id: int, movimiento_id: int,
            usuario_id: int, decision: str, justificacion: str,
            ip: str | None = None) -> RevisionTardio:
    movimiento = _movimiento(session, empresa_id, periodo_id, movimiento_id)
    fila = session.scalar(select(RevisionTardio).where(
        RevisionTardio.movimiento_id == movimiento.id).with_for_update())
    if fila is None:
        raise ValueError("La incidencia requiere revisión técnica previa.")
    if fila.decision is not None:
        raise ValueError("Ya existe decisión financiera sobre la incidencia.")
    if fila.revisado_por == usuario_id:
        raise ValueError("Quien revisó no puede autorizar su propia revisión.")
    if decision not in {"AUTORIZAR_GESTION", "RECHAZAR_GESTION"} or not justificacion.strip():
        raise ValueError("Decisión y justificación financiera obligatorias.")
    fila.decision = decision
    fila.justificacion_decision = justificacion.strip()
    fila.autorizado_por = usuario_id
    fila.autorizado_at = datetime.now(timezone.utc)
    registrar_auditoria(session, usuario_id=usuario_id, accion="WALLET_TARDIO_DECIDIR",
        entidad="wallets_tardios_revisiones", entidad_id=fila.id, empresa_id=empresa_id,
        antes={"decision": None},
        despues={"movimiento_id": movimiento_id, "periodo_id": periodo_id,
                 "decision": decision, "justificacion": fila.justificacion_decision,
                 "requiere_reapertura_si_cerrado": decision == "AUTORIZAR_GESTION"}, ip=ip)
    return fila


def listar_revisiones(session: Session, *, empresa_id: int, periodo_id: int) -> list[RevisionTardio]:
    ids = select(MovimientoTardio.id).where(
        MovimientoTardio.empresa_id == empresa_id, MovimientoTardio.periodo_id == periodo_id)
    return list(session.scalars(select(RevisionTardio).where(
        RevisionTardio.movimiento_id.in_(ids)).order_by(RevisionTardio.id)))
