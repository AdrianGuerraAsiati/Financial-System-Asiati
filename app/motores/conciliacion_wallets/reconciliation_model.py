"""Ejecuciones de Wallets cuya vigencia no se puede inferir del ID de una carga reutilizable."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class WiilogReconciliation(Base):
    __tablename__ = "wiilog_reconciliations"
    __table_args__ = (
        UniqueConstraint(
            "periodo_id", "carga_ordenes_id", "carga_wallet_id",
            name="uq_wiilog_reconciliations_pair",
        ),
        Index("ix_wiilog_reconciliations_periodo_id", "periodo_id", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodos.id", ondelete="RESTRICT"))
    carga_ordenes_id: Mapped[int] = mapped_column(ForeignKey("cargas.id", ondelete="RESTRICT"))
    carga_wallet_id: Mapped[int] = mapped_column(ForeignKey("cargas.id", ondelete="RESTRICT"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"))
    creado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TiendaReconciliation(Base):
    __tablename__ = "tienda_reconciliations"
    __table_args__ = (
        UniqueConstraint(
            "periodo_id", "carga_ordenes_id", "carga_wallet_id",
            name="uq_tienda_reconciliations_pair",
        ),
        Index("ix_tienda_reconciliations_periodo_wallet_id", "periodo_id", "wallet_email", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodos.id", ondelete="RESTRICT"))
    wallet_email: Mapped[str] = mapped_column(String(320), nullable=False)
    carga_ordenes_id: Mapped[int] = mapped_column(ForeignKey("cargas.id", ondelete="RESTRICT"))
    carga_wallet_id: Mapped[int] = mapped_column(ForeignKey("cargas.id", ondelete="RESTRICT"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"))
    creado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
