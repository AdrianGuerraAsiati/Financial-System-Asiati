from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
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


class CompraSnapshot(Base):
    __tablename__ = "compras_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "empresa_id",
            "contenido_hash",
            name="uq_compras_snapshots_empresa_hash",
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
    lineas: Mapped[int] = mapped_column(Integer, nullable=False)
    esquema_valido: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rangos_por_pais: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    diagnosticos: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)


class CompraSnapshotLinea(Base):
    __tablename__ = "compras_snapshot_lineas"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "pais",
            "fila_fuente",
            name="uq_compras_snapshot_linea_fuente",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("compras_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    pais: Mapped[str] = mapped_column(String(2), nullable=False)
    hoja_fuente: Mapped[str] = mapped_column(String(255), nullable=False)
    fila_fuente: Mapped[int] = mapped_column(Integer, nullable=False)
    crudo: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    normalizado: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
