from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ReglaCategorizacion(Base):
    __tablename__ = "reglas_categorizacion"
    __table_args__ = (
        CheckConstraint(
            "tipo_match IN ('EXACTO', 'EMPIEZA_CON', 'CONTIENE', 'REGEX')",
            name="ck_reglas_categorizacion_tipo_match",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    motor_slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    fuente_id: Mapped[int | None] = mapped_column(
        ForeignKey("fuentes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    patron: Mapped[str] = mapped_column(Text, nullable=False)
    tipo_match: Mapped[str] = mapped_column(String(20), nullable=False)
    prioridad: Mapped[int] = mapped_column(Integer, nullable=False)
    condiciones: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Las siete dimensiones del contrato. "tipo" representa la dimensión
    # ingreso/egreso; puede quedar NULL mientras el movimiento está PENDIENTE.
    tipo: Mapped[str | None] = mapped_column(String(32), nullable=True)
    unidad_negocio: Mapped[str | None] = mapped_column(String(255), nullable=True)
    categoria: Mapped[str | None] = mapped_column(String(255), nullable=True)
    empresa: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tercero: Mapped[str | None] = mapped_column(String(255), nullable=True)
    modalidad: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fijo_variable: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Ciudad existe en la hoja contable, pero no forma parte de las siete
    # dimensiones acordadas por el catálogo de wallets.
    ciudad: Mapped[str | None] = mapped_column(String(255), nullable=True)

    requiere_revision: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    activa: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    origen: Mapped[str | None] = mapped_column(String(100), nullable=True)
    veces_aplicada: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    creado_por: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )
    creado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Movimiento(Base):
    __tablename__ = "movimientos"
    __table_args__ = (
        UniqueConstraint(
            "carga_id",
            "hash_fila",
            name="uq_movimientos_carga_hash_fila",
        ),
        CheckConstraint(
            "estado_categoria IN ('AUTO', 'REVISAR', 'PENDIENTE', 'MANUAL')",
            name="ck_movimientos_estado_categoria",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fuente_id: Mapped[int] = mapped_column(
        ForeignKey("fuentes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    carga_id: Mapped[int] = mapped_column(
        ForeignKey("cargas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    periodo_id: Mapped[int] = mapped_column(
        ForeignKey("periodos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    fecha_pago_oportuno: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    tipo: Mapped[str | None] = mapped_column(String(32), nullable=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    ciudad: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unidad_negocio: Mapped[str | None] = mapped_column(String(255), nullable=True)
    categoria: Mapped[str | None] = mapped_column(String(255), nullable=True)
    empresa: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tercero: Mapped[str | None] = mapped_column(String(255), nullable=True)
    modalidad: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fijo_variable: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recibo_pago_caja: Mapped[str | None] = mapped_column(Text, nullable=True)
    causacion: Mapped[str | None] = mapped_column(Text, nullable=True)

    descripcion_norm: Mapped[str] = mapped_column(Text, nullable=False)
    estado_categoria: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="PENDIENTE",
        server_default="PENDIENTE",
        index=True,
    )
    regla_id: Mapped[int | None] = mapped_column(
        ForeignKey("reglas_categorizacion.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    categorizado_por: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=True,
    )
    categorizado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    referencia_externa: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hash_fila: Mapped[str] = mapped_column(String(64), nullable=False)
    crudo: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
