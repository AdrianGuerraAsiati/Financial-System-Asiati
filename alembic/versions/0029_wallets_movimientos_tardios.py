"""Registro de incidencias temporales, nunca aplica movimientos.

Revision ID: 0029_wallets_tardios
Revises: 0028_wallets_corte
"""
from alembic import op
import sqlalchemy as sa

revision = "0029_wallets_tardios"
down_revision = "0028_wallets_corte"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "wallets_movimientos_tardios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("periodo_id", sa.Integer(), sa.ForeignKey("periodos.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("corte_id", sa.Integer(), sa.ForeignKey("wallets_cortes_operativos.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("identificador_externo", sa.String(320), nullable=False),
        sa.Column("tipo_wallet", sa.String(16), nullable=False),
        sa.Column("identidad_wallet", sa.String(320), nullable=False),
        sa.Column("instante_movimiento", sa.DateTime(timezone=True), nullable=False),
        sa.Column("instante_recepcion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clasificacion", sa.String(32), nullable=False),
        sa.Column("evidencia_ref", sa.String(512), nullable=False),
        sa.Column("registrado_por", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("creado_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["periodo_id", "empresa_id"], ["periodos.id", "periodos.empresa_id"], name="fk_wallets_tardios_periodo_empresa", ondelete="RESTRICT"),
        sa.UniqueConstraint("periodo_id", "tipo_wallet", "identidad_wallet", "identificador_externo", name="uq_wallets_tardios_identificador"),
        sa.CheckConstraint("clasificacion IN ('TARDIO_DEL_PERIODO','POST_CORTE')", name="ck_wallets_tardios_clasificacion"),
    )

def downgrade() -> None:
    op.drop_table("wallets_movimientos_tardios")
