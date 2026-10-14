"""Incidencias temporales auditablemente registradas; no son asientos financieros."""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, UniqueConstraint, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.auditoria import registrar_auditoria
from app.core.db import Base
from app.core.periodos import Periodo
from .corte_operativo import CorteOperativo, clasificar_movimiento
from .catalogo_admin import validar_identidad


class MovimientoTardio(Base):
    __tablename__ = "wallets_movimientos_tardios"
    __table_args__ = (
        ForeignKeyConstraint(["periodo_id", "empresa_id"], ["periodos.id", "periodos.empresa_id"], name="fk_wallets_tardios_periodo_empresa", ondelete="RESTRICT"),
        UniqueConstraint("periodo_id", "tipo_wallet", "identidad_wallet", "identificador_externo", name="uq_wallets_tardios_identificador"),
        CheckConstraint("clasificacion IN ('TARDIO_DEL_PERIODO','POST_CORTE')", name="ck_wallets_tardios_clasificacion"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=False)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodos.id", ondelete="RESTRICT"), nullable=False)
    corte_id: Mapped[int] = mapped_column(ForeignKey("wallets_cortes_operativos.id", ondelete="RESTRICT"), nullable=False)
    identificador_externo: Mapped[str] = mapped_column(String(320), nullable=False)
    tipo_wallet: Mapped[str] = mapped_column(String(16), nullable=False)
    identidad_wallet: Mapped[str] = mapped_column(String(320), nullable=False)
    instante_movimiento: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    instante_recepcion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    clasificacion: Mapped[str] = mapped_column(String(32), nullable=False)
    evidencia_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    registrado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    creado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


def registrar(session: Session, *, empresa_id: int, periodo_id: int,
              usuario_id: int, tipo_wallet: str, identidad_wallet: str | None,
              identificador_externo: str, instante_movimiento: datetime,
              instante_recepcion: datetime, evidencia_ref: str,
              ip: str | None = None) -> MovimientoTardio:
    periodo = session.scalar(select(Periodo).where(Periodo.id == periodo_id,
        Periodo.empresa_id == empresa_id).with_for_update())
    if periodo is None:
        raise LookupError("Período no encontrado para la empresa.")
    corte = session.scalar(select(CorteOperativo).where(
        CorteOperativo.periodo_id == periodo_id, CorteOperativo.empresa_id == empresa_id))
    if corte is None:
        raise ValueError("No existe corte operativo declarado para el período.")
    tipo, identidad = validar_identidad(tipo_wallet, identidad_wallet)
    externo = identificador_externo.strip()
    evidencia = evidencia_ref.strip()
    if not externo or len(externo) > 320 or not evidencia or len(evidencia) > 512:
        raise ValueError("Identificador externo y referencia de evidencia son obligatorios.")
    clase = clasificar_movimiento(instante_movimiento=instante_movimiento,
        instante_recepcion=instante_recepcion, corte_utc=corte.corte_utc)
    if clase == "EN_CORTE":
        raise ValueError("Movimiento en corte: no corresponde registrarlo como incidencia tardía.")
    # Admite reportar una incidencia aun si el período está cerrado; nunca altera sus datos financieros.
    if session.scalar(select(MovimientoTardio.id).where(
        MovimientoTardio.periodo_id == periodo_id,
        MovimientoTardio.tipo_wallet == tipo,
        MovimientoTardio.identidad_wallet == identidad,
        MovimientoTardio.identificador_externo == externo)) is not None:
        raise ValueError("La incidencia ya existe para esta wallet y período.")
    item = MovimientoTardio(empresa_id=empresa_id, periodo_id=periodo_id, corte_id=corte.id,
        tipo_wallet=tipo, identidad_wallet=identidad, identificador_externo=externo,
        instante_movimiento=instante_movimiento, instante_recepcion=instante_recepcion,
        clasificacion=clase, evidencia_ref=evidencia, registrado_por=usuario_id)
    session.add(item)
    session.flush()
    registrar_auditoria(session, usuario_id=usuario_id, accion="WALLET_MOVIMIENTO_TARDIO_DETECTAR",
        entidad="wallets_movimientos_tardios", entidad_id=item.id, empresa_id=empresa_id,
        despues={"periodo_id": periodo_id, "tipo_wallet": tipo, "identidad_wallet": identidad,
                 "identificador_externo": externo, "clasificacion": clase,
                 "instante_movimiento": instante_movimiento.isoformat(),
                 "instante_recepcion": instante_recepcion.isoformat(),
                 "evidencia_ref": evidencia, "periodo_cerrado": periodo.cerrado}, ip=ip)
    return item


def listar(session: Session, *, empresa_id: int, periodo_id: int) -> list[MovimientoTardio]:
    periodo = session.get(Periodo, periodo_id)
    if periodo is None or periodo.empresa_id != empresa_id:
        raise LookupError("Período no encontrado para la empresa.")
    return list(session.scalars(select(MovimientoTardio).where(
        MovimientoTardio.empresa_id == empresa_id,
        MovimientoTardio.periodo_id == periodo_id).order_by(MovimientoTardio.id)))
