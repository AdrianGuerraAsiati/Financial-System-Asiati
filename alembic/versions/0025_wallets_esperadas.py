"""Catálogo de cobertura esperada de Wallets por empresa/período.

Revision ID: 0025_wallets_esperadas
Revises: 0024_wallets_historial
"""
from alembic import op
import sqlalchemy as sa

revision = "0025_wallets_esperadas"
down_revision = "0024_wallets_historial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_periodos_id_empresa", "periodos", ["id", "empresa_id"])
    op.create_table(
        "wallets_esperadas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("periodo_id", sa.Integer(), sa.ForeignKey("periodos.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tipo_wallet", sa.String(16), nullable=False),
        sa.Column("identidad_wallet", sa.String(320), nullable=False, server_default=""),
        sa.Column("registrado_por", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("registrado_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("tipo_wallet IN ('wiilog','tienda','pagos')", name="ck_wallets_esperadas_tipo"),
        sa.CheckConstraint("(tipo_wallet = 'wiilog' AND identidad_wallet = '') OR (tipo_wallet <> 'wiilog' AND identidad_wallet <> '')", name="ck_wallets_esperadas_identidad"),
        sa.ForeignKeyConstraint(["periodo_id", "empresa_id"], ["periodos.id", "periodos.empresa_id"], name="fk_wallets_esperadas_periodo_empresa", ondelete="RESTRICT"),
        sa.UniqueConstraint("periodo_id", "tipo_wallet", "identidad_wallet", name="uq_wallets_esperadas_contexto"),
    )
    op.create_index("ix_wallets_esperadas_empresa_periodo", "wallets_esperadas", ["empresa_id", "periodo_id"])


def downgrade() -> None:
    op.drop_index("ix_wallets_esperadas_empresa_periodo", table_name="wallets_esperadas")
    op.drop_table("wallets_esperadas")
    op.drop_constraint("uq_periodos_id_empresa", "periodos", type_="unique")
