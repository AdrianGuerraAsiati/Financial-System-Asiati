"""Facturas de compra a proveedores y pagos manuales."""
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class FacturaCompra(Base):
    __tablename__ = "tesoreria_facturas"
    __table_args__ = (
        UniqueConstraint("empresa_id", "proveedor_clave", "numero_clave", name="uq_tes_factura_proveedor_numero"),
        UniqueConstraint("empresa_id", "archivo_hash", name="uq_tes_factura_archivo_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True, nullable=False)
    numero: Mapped[str] = mapped_column(String(120), nullable=False)
    numero_clave: Mapped[str] = mapped_column(String(120), nullable=False)
    proveedor: Mapped[str] = mapped_column(String(255), nullable=False)
    proveedor_clave: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha_emision: Mapped[date | None] = mapped_column(Date)
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="COP")
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    ciudad: Mapped[str | None] = mapped_column(String(100))
    unidad_negocio: Mapped[str | None] = mapped_column(String(120))
    categoria: Mapped[str | None] = mapped_column(String(120))
    fijo_variable: Mapped[str | None] = mapped_column(String(120))
    cuenta_pago: Mapped[str | None] = mapped_column(String(200))
    documento_contable: Mapped[str | None] = mapped_column(String(120))
    archivo_nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    archivo_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    archivo_tipo: Mapped[str] = mapped_column(String(80), nullable=False)
    archivo_ruta: Mapped[str] = mapped_column(String(500), nullable=False)
    creado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    creado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PagoFactura(Base):
    __tablename__ = "tesoreria_pagos"
    __table_args__ = (
        UniqueConstraint("factura_id", "soporte_hash", name="uq_tes_pago_factura_soporte"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    factura_id: Mapped[int] = mapped_column(ForeignKey("tesoreria_facturas.id"), nullable=False, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    referencia: Mapped[str | None] = mapped_column(String(120))
    soporte_nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    soporte_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    soporte_tipo: Mapped[str] = mapped_column(String(80), nullable=False)
    soporte_ruta: Mapped[str] = mapped_column(String(500), nullable=False)
    registrado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    creado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
