from typing import Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Hallazgo(Base):
    __tablename__ = "hallazgos"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('detectado', 'en_gestion', 'escalado', 'resuelto', 'cerrado')",
            name="ck_hallazgos_estado",
        ),
        Index(
            "uq_hallazgos_periodo_motor_clave",
            "periodo_id",
            "motor_slug",
            "clave",
            unique=True,
            postgresql_where=text("clave IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    periodo_id: Mapped[int] = mapped_column(
        ForeignKey("periodos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    critico: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    resuelto: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    # Flujo de caso especial (escalamiento.ESTADOS). `resuelto` se mantiene
    # porque la política de cierre lo usa; resolver actualiza ambos.
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="detectado",
        server_default="detectado",
        index=True,
    )
    motor_slug: Mapped[str | None] = mapped_column(String(100), nullable=True)
    codigo_regla: Mapped[str | None] = mapped_column(String(120), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidencia: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Identifica el mismo problema entre cargas (p. ej. wallet + regla + mov_id). Ver sincronizacion.py.
    clave: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # True solo si lo resolvió la sincronización porque el problema ya no aparece en la carga nueva.
    resuelto_por_sistema: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
