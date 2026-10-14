"""Vigencia declarada de wallets, sin inventar fechas históricas.

Revision ID: 0027_wallets_vigencia
Revises: 0026_wallets_aprobaciones
"""
from alembic import op
import sqlalchemy as sa

revision = "0027_wallets_vigencia"
down_revision = "0026_wallets_aprobaciones"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("wallets_esperadas", sa.Column("vigente_desde", sa.Date(), nullable=True))
    op.add_column("wallets_esperadas", sa.Column("vigente_hasta", sa.Date(), nullable=True))
    op.create_check_constraint(
        "ck_wallets_esperadas_vigencia_orden",
        "wallets_esperadas",
        "(vigente_desde IS NULL OR vigente_hasta IS NULL OR vigente_desde <= vigente_hasta)",
    )

def downgrade() -> None:
    op.drop_constraint("ck_wallets_esperadas_vigencia_orden", "wallets_esperadas", type_="check")
    op.drop_column("wallets_esperadas", "vigente_hasta")
    op.drop_column("wallets_esperadas", "vigente_desde")
