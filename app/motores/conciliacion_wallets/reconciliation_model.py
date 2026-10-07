"""Ejecuciones de Wiilog: la pareja de cargas no identifica su orden de ejecución."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint, func
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
