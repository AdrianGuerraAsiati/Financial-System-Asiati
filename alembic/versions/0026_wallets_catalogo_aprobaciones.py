"""Aprobación inmutable de cobertura por período.

Revision ID: 0026_wallets_aprobaciones
Revises: 0025_wallets_esperadas
"""
from alembic import op
import sqlalchemy as sa

revision = "0026_wallets_aprobaciones"
down_revision = "0025_wallets_esperadas"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "wallets_catalogo_aprobaciones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("periodo_id", sa.Integer(), sa.ForeignKey("periodos.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("aprobado_por", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("aprobado_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("wallets_snapshot", sa.JSON(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["periodo_id", "empresa_id"], ["periodos.id", "periodos.empresa_id"], name="fk_wallets_aprobacion_periodo_empresa", ondelete="RESTRICT"),
        sa.UniqueConstraint("periodo_id", name="uq_wallets_aprobacion_periodo"),
    )

def downgrade() -> None:
    op.drop_table("wallets_catalogo_aprobaciones")
