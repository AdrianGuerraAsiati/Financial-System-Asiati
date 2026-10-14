"""Evidencia inmutable de respuestas de ejecución; no recalcula motores ni cambia hallazgos."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, select, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base
from app.core.periodos import Periodo


class WalletEjecucionHistorial(Base):
    __tablename__ = "wallets_ejecuciones_historial"
    __table_args__ = (
        Index("ix_wallets_historial_contexto", "empresa_id", "periodo_id", "tipo_wallet", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=False)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodos.id", ondelete="RESTRICT"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    tipo_wallet: Mapped[str] = mapped_column(String(16), nullable=False)
    identidad_wallet: Mapped[str | None] = mapped_column(String(320))
    carga_wallet_id: Mapped[int] = mapped_column(ForeignKey("cargas.id", ondelete="RESTRICT"), nullable=False)
    carga_ordenes_id: Mapped[int | None] = mapped_column(ForeignKey("cargas.id", ondelete="RESTRICT"))
    bloqueado: Mapped[bool] = mapped_column(Boolean, nullable=False)
    resultado: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    creado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def guardar_historial(session: Session, *, empresa_id: int, periodo_id: int,
                     usuario_id: int, tipo_wallet: str, identidad_wallet: str | None,
                     resultado: dict[str, Any]) -> WalletEjecucionHistorial:
    cargas = resultado["cargas"]
    registro = WalletEjecucionHistorial(
        empresa_id=empresa_id, periodo_id=periodo_id, usuario_id=usuario_id,
        tipo_wallet=tipo_wallet, identidad_wallet=(identidad_wallet or "").strip().lower() or None,
        carga_wallet_id=cargas["wallet_id"], carga_ordenes_id=cargas.get("ordenes_id"),
        bloqueado=bool(resultado["bloqueado"]), resultado=resultado,
    )
    session.add(registro)
    session.flush()
    return registro


def listar_historial(session: Session, *, empresa_id: int, periodo_id: int,
                   tipo_wallet: str, identidad_wallet: str | None = None,
                   limite: int = 20) -> list[WalletEjecucionHistorial]:
    periodo = session.get(Periodo, periodo_id)
    if periodo is None or periodo.empresa_id != empresa_id:
        raise ValueError("El período no pertenece a la empresa indicada.")
    consulta = select(WalletEjecucionHistorial).where(
        WalletEjecucionHistorial.empresa_id == empresa_id,
        WalletEjecucionHistorial.periodo_id == periodo_id,
        WalletEjecucionHistorial.tipo_wallet == tipo_wallet,
    )
    if tipo_wallet in ("tienda", "pagos"):
        if not identidad_wallet or not identidad_wallet.strip():
            raise ValueError("La identidad de la wallet es obligatoria.")
        consulta = consulta.where(WalletEjecucionHistorial.identidad_wallet == identidad_wallet.strip().lower())
    return list(session.scalars(consulta.order_by(WalletEjecucionHistorial.id.desc()).limit(limite)))
