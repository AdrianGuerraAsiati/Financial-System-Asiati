"""Ingresos reportados, sin confirmar ni aplicar a Cartera.

Revision ID: 0023_recaudos_ingresos_reportados
Revises: 0022_tesoreria_facturas
"""
from alembic import op
import sqlalchemy as sa

revision = "0023_recaudos_ingresos_reportados"
down_revision = "0022_tesoreria_facturas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recaudos_ingresos_reportados",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("fecha_reportada", sa.Date(), nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("cuenta_receptora", sa.String(200), nullable=False),
        sa.Column("cuenta_clave", sa.String(200), nullable=False),
        sa.Column("referencia_origen", sa.String(120), nullable=False),
        sa.Column("referencia_clave", sa.String(120), nullable=False),
        sa.Column("pagador_reportado", sa.String(255), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("origen", sa.String(24), nullable=False, server_default="MANUAL"),
        sa.Column("estado", sa.String(32), nullable=False, server_default="PENDIENTE_VERIFICACION"),
        sa.Column("registrado_por", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("registrado_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("empresa_id", "cuenta_clave", "referencia_clave", name="uq_recaudos_empresa_cuenta_referencia"),
        sa.CheckConstraint("monto > 0", name="ck_recaudos_monto_positivo"),
        sa.CheckConstraint("moneda IN ('COP','USD','CLP')", name="ck_recaudos_moneda"),
        sa.CheckConstraint("origen = 'MANUAL'", name="ck_recaudos_origen_v1"),
        sa.CheckConstraint("estado = 'PENDIENTE_VERIFICACION'", name="ck_recaudos_estado_v1"),
    )
    op.create_index("ix_recaudos_empresa_fecha", "recaudos_ingresos_reportados", ["empresa_id", "fecha_reportada"])


def downgrade() -> None:
    op.drop_index("ix_recaudos_empresa_fecha", table_name="recaudos_ingresos_reportados")
    op.drop_table("recaudos_ingresos_reportados")
