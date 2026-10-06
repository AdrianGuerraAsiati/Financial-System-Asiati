from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DimensionValor(Base):
    """Un valor de una lista de categorización. Nunca se borra: se desactiva."""

    __tablename__ = "dimension_valores"
    __table_args__ = (
        CheckConstraint(
            "dimension IN ('ingreso_egreso', 'unidad_negocio', 'categoria', 'empresa', 'fijo_variable')",
            name="ck_dimension_valores_dimension",
        ),
        UniqueConstraint("dimension", "valor_normalizado", name="uq_dimension_valores_normalizado"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dimension: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    valor: Mapped[str] = mapped_column(String(120), nullable=False)
    # Mayúsculas, sin tildes y sin espacios sobrantes: así no se repite "Consultoría" y "CONSULTORIA".
    valor_normalizado: Mapped[str] = mapped_column(String(120), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    creado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    actualizado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
