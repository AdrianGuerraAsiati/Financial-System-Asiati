"""Bandeja de abonos reportados, separada de Tesorería CxP y Cartera CxC."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class IngresoReportado(Base):
    __tablename__ = "recaudos_ingresos_reportados"
    __table_args__ = (
        UniqueConstraint(
            "empresa_id", "cuenta_clave", "referencia_clave",
            name="uq_recaudos_empresa_cuenta_referencia",
        ),
        CheckConstraint("monto > 0", name="ck_recaudos_monto_positivo"),
        CheckConstraint("moneda IN ('COP','USD','CLP')", name="ck_recaudos_moneda"),
        CheckConstraint("origen = 'MANUAL'", name="ck_recaudos_origen_v1"),
        CheckConstraint("estado = 'PENDIENTE_VERIFICACION'", name="ck_recaudos_estado_v1"),
        Index("ix_recaudos_empresa_fecha", "empresa_id", "fecha_reportada"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=False)
    fecha_reportada: Mapped[date] = mapped_column(Date, nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    cuenta_receptora: Mapped[str] = mapped_column(String(200), nullable=False)
    cuenta_clave: Mapped[str] = mapped_column(String(200), nullable=False)
    referencia_origen: Mapped[str] = mapped_column(String(120), nullable=False)
    referencia_clave: Mapped[str] = mapped_column(String(120), nullable=False)
    pagador_reportado: Mapped[str | None] = mapped_column(String(255))
    descripcion: Mapped[str | None] = mapped_column(Text)
    origen: Mapped[str] = mapped_column(String(24), nullable=False, server_default="MANUAL")
    estado: Mapped[str] = mapped_column(String(32), nullable=False, server_default="PENDIENTE_VERIFICACION")
    registrado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    registrado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
