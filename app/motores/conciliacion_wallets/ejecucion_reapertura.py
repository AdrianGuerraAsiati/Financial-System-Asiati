"""Ejecución de reapertura autorizada, sin correcciones de saldo."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from app.core.db import Base
from app.core.periodos import Periodo
from app.core.periodos.service import reabrir_periodo
from app.core.auditoria import registrar_auditoria
from .solicitudes_reapertura import SolicitudReapertura

class EjecucionReapertura(Base):
    __tablename__ = "wallets_ejecuciones_reapertura"
    __table_args__ = (
        UniqueConstraint("solicitud_id", name="uq_wallets_ejecucion_solicitud"),
        ForeignKeyConstraint(["periodo_id","empresa_id"],["periodos.id","periodos.empresa_id"],name="fk_wallets_ejecucion_periodo_empresa",ondelete="RESTRICT"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodos.id"), nullable=False)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("wallets_solicitudes_reapertura.id"), nullable=False)
    ejecutado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    ejecutado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    plan_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    evidencia_previa_ref: Mapped[str] = mapped_column(String(512), nullable=False)

def ejecutar(session: Session, *, empresa_id: int, periodo_id: int, solicitud_id: int,
            usuario_id: int, motivo: str, plan_ref: str, evidencia_previa_ref: str,
            ip: str | None = None) -> EjecucionReapertura:
    periodo = session.scalar(select(Periodo).where(
        Periodo.id == periodo_id, Periodo.empresa_id == empresa_id).with_for_update())
    if periodo is None:
        raise LookupError("Período no encontrado para la empresa.")
    if not periodo.cerrado:
        raise ValueError("El período ya está abierto.")
    solicitud = session.scalar(select(SolicitudReapertura).where(
        SolicitudReapertura.id == solicitud_id,
        SolicitudReapertura.empresa_id == empresa_id,
        SolicitudReapertura.periodo_id == periodo_id).with_for_update())
    if solicitud is None:
        raise LookupError("Solicitud no encontrada para el período y empresa.")
    if solicitud.decision != "APROBADA" or solicitud.decidido_por != usuario_id:
        raise ValueError("Solo el Superadministrador que aprobó la solicitud puede ejecutarla.")
    if usuario_id == solicitud.solicitado_por:
        raise ValueError("No puede ejecutar una solicitud propia.")
    if session.scalar(select(EjecucionReapertura.id).where(
        EjecucionReapertura.solicitud_id == solicitud_id)) is not None:
        raise ValueError("La solicitud ya fue ejecutada.")
    valores = (motivo.strip(), plan_ref.strip(), evidencia_previa_ref.strip())
    if not all(valores) or len(valores[1]) > 512 or len(valores[2]) > 512:
        raise ValueError("Se exige motivo, referencia del plan y evidencia previa.")
    registro = EjecucionReapertura(
        empresa_id=empresa_id, periodo_id=periodo_id, solicitud_id=solicitud_id,
        ejecutado_por=usuario_id, motivo=valores[0],
        plan_ref=valores[1], evidencia_previa_ref=valores[2])
    evento = reabrir_periodo(session, periodo, actor=f"usuario:{usuario_id}",
                            motivo=f"Solicitud Wallets #{solicitud_id}: {valores[0]}")
    session.add(registro)
    session.flush()
    session.flush()
    registrar_auditoria(session, usuario_id=usuario_id, accion="WALLET_REAPERTURA_EJECUTAR",
        entidad="wallets_ejecuciones_reapertura", entidad_id=registro.id,
        empresa_id=empresa_id, antes={"periodo_cerrado": True},
        despues={"periodo_cerrado": False, "solicitud_id": solicitud_id,
                 "evento_cierre_id": evento.id, "plan_ref": valores[1],
                 "evidencia_previa_ref": valores[2], "motivo": valores[0]}, ip=ip)
    return registro
