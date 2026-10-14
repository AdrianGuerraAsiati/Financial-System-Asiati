"""Definición auditable de corte operativo; sin valores implícitos.

Revision ID: 0028_wallets_corte
Revises: 0027_wallets_vigencia
"""
from alembic import op
import sqlalchemy as sa

revision = "0028_wallets_corte"
down_revision = "0027_wallets_vigencia"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "wallets_cortes_operativos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("periodo_id", sa.Integer(), sa.ForeignKey("periodos.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("zona_horaria", sa.String(100), nullable=False),
        sa.Column("corte_local", sa.DateTime(timezone=False), nullable=False),
        sa.Column("corte_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registrado_por", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("creado_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["periodo_id", "empresa_id"], ["periodos.id", "periodos.empresa_id"], name="fk_wallets_corte_periodo_empresa", ondelete="RESTRICT"),
        sa.UniqueConstraint("periodo_id", name="uq_wallets_corte_periodo"),
    )

def downgrade() -> None:
    op.drop_table("wallets_cortes_operativos")
