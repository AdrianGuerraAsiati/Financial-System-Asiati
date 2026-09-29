from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SourceRefreshState(Base):
    """Estado de coalescencia para cambios provenientes de Google Sheets."""

    __tablename__ = "source_refresh_states"
    __table_args__ = (
        UniqueConstraint(
            "empresa_id",
            "modulo",
            name="uq_source_refresh_states_empresa_modulo",
        ),
        CheckConstraint(
            "estado IN ('IDLE', 'PENDING', 'REFRESHING', 'ERROR')",
            name="ck_source_refresh_states_estado",
        ),
        CheckConstraint(
            "modulo IN ('cartera', 'compras')",
            name="ck_source_refresh_states_modulo",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    modulo: Mapped[str] = mapped_column(String(32), nullable=False)
    estado: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="IDLE",
        server_default="IDLE",
        index=True,
    )
    first_event_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_event_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    processed_through_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_refresh_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    event_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
