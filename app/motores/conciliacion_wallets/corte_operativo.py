"""Contrato de corte explícito y de solo diagnóstico, sin cierres financieros."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base
from app.core.periodos import Periodo
from app.core.auditoria import registrar_auditoria


ZONA_HORARIA_OFICIAL = "America/Bogota"


class CorteOperativo(Base):
    __tablename__ = "wallets_cortes_operativos"
    __table_args__ = (
        ForeignKeyConstraint(["periodo_id", "empresa_id"], ["periodos.id", "periodos.empresa_id"], name="fk_wallets_corte_periodo_empresa", ondelete="RESTRICT"),
        UniqueConstraint("periodo_id", name="uq_wallets_corte_periodo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=False)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodos.id", ondelete="RESTRICT"), nullable=False)
    zona_horaria: Mapped[str] = mapped_column(String(100), nullable=False)
    corte_local: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    corte_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registrado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    creado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    motivo: Mapped[str] = mapped_column(Text, nullable=False)


def validar_corte(zona_horaria: str, corte_local: datetime, periodo: Periodo) -> datetime:
    if zona_horaria != ZONA_HORARIA_OFICIAL:
        raise ValueError("La zona horaria oficial del corte es America/Bogota.")
    if corte_local.tzinfo is not None:
        raise ValueError("La fecha/hora local no debe incluir zona u offset.")
    try:
        zona = ZoneInfo(zona_horaria)
    except (ZoneInfoNotFoundError, ValueError, KeyError) as exc:
        raise ValueError("Zona horaria IANA inválida.") from exc
    if not periodo.fecha_inicio <= corte_local.date() <= periodo.fecha_fin:
        raise ValueError("El corte debe pertenecer a las fechas del período.")
    local = corte_local.replace(tzinfo=zona)
    utc = local.astimezone(timezone.utc)
    if utc.astimezone(zona).replace(tzinfo=None) != corte_local:
        raise ValueError("Hora local inexistente por transición horaria.")
    if local.replace(fold=1).utcoffset() != local.replace(fold=0).utcoffset():
        raise ValueError("Hora local ambigua por transición horaria.")
    return utc


def configurar_corte(session: Session, *, empresa_id: int, periodo_id: int,
                     usuario_id: int, zona_horaria: str, corte_local: datetime,
                     motivo: str, ip: str | None = None) -> CorteOperativo:
    periodo = session.scalar(select(Periodo).where(
        Periodo.id == periodo_id, Periodo.empresa_id == empresa_id
    ).with_for_update())
    if periodo is None:
        raise LookupError("Período no encontrado para la empresa.")
    if periodo.cerrado:
        raise ValueError("No se configura el corte de un período cerrado.")
    if not motivo.strip():
        raise ValueError("Se requiere justificación del corte.")
    existente = session.scalar(select(CorteOperativo).where(CorteOperativo.periodo_id == periodo_id))
    if existente:
        raise ValueError("El corte ya está configurado; no se permite sobrescribir sin proceso de revisión.")
    utc = validar_corte(zona_horaria, corte_local, periodo)
    fila = CorteOperativo(empresa_id=empresa_id, periodo_id=periodo_id,
                         registrado_por=usuario_id, zona_horaria=zona_horaria,
                         corte_local=corte_local, corte_utc=utc, motivo=motivo.strip())
    session.add(fila)
    session.flush()
    registrar_auditoria(session, usuario_id=usuario_id, accion="WALLET_CORTE_REGISTRAR",
        entidad="wallets_cortes_operativos", entidad_id=fila.id, empresa_id=empresa_id,
        despues={"periodo_id": periodo_id, "zona_horaria": zona_horaria,
                 "corte_local": corte_local.isoformat(), "corte_utc": utc.isoformat(),
                 "motivo": motivo.strip()}, ip=ip)
    return fila


def consultar_corte(session: Session, *, empresa_id: int, periodo_id: int) -> CorteOperativo | None:
    periodo = session.get(Periodo, periodo_id)
    if periodo is None or periodo.empresa_id != empresa_id:
        raise LookupError("Período no encontrado para la empresa.")
    return session.scalar(select(CorteOperativo).where(
        CorteOperativo.empresa_id == empresa_id, CorteOperativo.periodo_id == periodo_id
    ))


def clasificar_movimiento(*, instante_movimiento: datetime, instante_recepcion: datetime,
                         corte_utc: datetime) -> str:
    """Clasifica usando dos instantes verificables; no modifica contabilidad."""
    if any(v.tzinfo is None or v.utcoffset() is None for v in
           (instante_movimiento, instante_recepcion, corte_utc)):
        raise ValueError("Todos los instantes deben incluir zona horaria.")
    if instante_movimiento > corte_utc:
        return "POST_CORTE"
    if instante_recepcion > corte_utc:
        return "TARDIO_DEL_PERIODO"
    return "EN_CORTE"
