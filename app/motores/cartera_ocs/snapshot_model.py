from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CarteraSnapshot(Base):
    __tablename__ = "cartera_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "empresa_id",
            "contenido_hash",
            name="uq_cartera_snapshots_empresa_hash",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    spreadsheet_id: Mapped[str] = mapped_column(String(255), nullable=False)
    modo_fuente: Mapped[str] = mapped_column(String(50), nullable=False)
    contenido_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    cargado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    guardado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    filas: Mapped[int] = mapped_column(Integer, nullable=False)
    operaciones: Mapped[int] = mapped_column(Integer, nullable=False)
    registros_mora: Mapped[int] = mapped_column(Integer, nullable=False)
    proyecciones: Mapped[int] = mapped_column(Integer, nullable=False)
    rangos: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    diagnosticos: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
    )


class CarteraSnapshotFila(Base):
    __tablename__ = "cartera_snapshot_filas"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "tipo",
            "fila_fuente",
            name="uq_cartera_snapshot_fila_fuente",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("cartera_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    fila_fuente: Mapped[int] = mapped_column(Integer, nullable=False)
    crudo: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    normalizado: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
