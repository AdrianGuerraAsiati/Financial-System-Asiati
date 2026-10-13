"""Registrar facturas de compra y pagos manuales.

Revision ID: 0022_tesoreria_facturas
Revises: 0021_cerrar_hallazgos_sin_clave
"""
from alembic import op
import sqlalchemy as sa

revision = "0022_tesoreria_facturas"
down_revision = "0021_cerrar_hallazgos_sin_clave"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("tesoreria_facturas",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("empresa_id", sa.Integer, sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("numero", sa.String(120), nullable=False),
        sa.Column("numero_clave", sa.String(120), nullable=False),
        sa.Column("proveedor", sa.String(255), nullable=False),
        sa.Column("proveedor_clave", sa.String(255), nullable=False),
        sa.Column("fecha_emision", sa.Date),
        sa.Column("fecha_vencimiento", sa.Date),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=False),
        sa.Column("ciudad", sa.String(100)),
        sa.Column("unidad_negocio", sa.String(120)),
        sa.Column("categoria", sa.String(120)),
        sa.Column("fijo_variable", sa.String(120)),
        sa.Column("cuenta_pago", sa.String(200)),
        sa.Column("documento_contable", sa.String(120)),
        sa.Column("archivo_nombre", sa.String(255), nullable=False),
        sa.Column("archivo_hash", sa.String(64), nullable=False),
        sa.Column("archivo_tipo", sa.String(80), nullable=False),
        sa.Column("archivo_ruta", sa.String(500), nullable=False),
        sa.Column("creado_por", sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("creado_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("empresa_id", "proveedor_clave", "numero_clave", name="uq_tes_factura_proveedor_numero"),
        sa.UniqueConstraint("empresa_id", "archivo_hash", name="uq_tes_factura_archivo_hash"),
        sa.CheckConstraint("monto > 0", name="ck_tes_factura_monto"),
    )
    op.create_index("ix_tes_facturas_empresa", "tesoreria_facturas", ["empresa_id"])
    op.create_table("tesoreria_pagos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("factura_id", sa.Integer, sa.ForeignKey("tesoreria_facturas.id"), nullable=False),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("referencia", sa.String(120)),
        sa.Column("soporte_nombre", sa.String(255), nullable=False),
        sa.Column("soporte_hash", sa.String(64), nullable=False),
        sa.Column("soporte_tipo", sa.String(80), nullable=False),
        sa.Column("soporte_ruta", sa.String(500), nullable=False),
        sa.Column("registrado_por", sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("creado_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("factura_id", "soporte_hash", name="uq_tes_pago_factura_soporte"),
        sa.CheckConstraint("monto > 0", name="ck_tes_pago_monto"),
    )
    op.create_index("ix_tes_pagos_factura", "tesoreria_pagos", ["factura_id"])


def downgrade() -> None:
    op.drop_index("ix_tes_pagos_factura", table_name="tesoreria_pagos")
    op.drop_table("tesoreria_pagos")
    op.drop_index("ix_tes_facturas_empresa", table_name="tesoreria_facturas")
    op.drop_table("tesoreria_facturas")
