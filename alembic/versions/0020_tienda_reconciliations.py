"""Track Tiendas file pairs and execution order independently of reusable loads.

Revision ID: 0020_tienda_reconciliations
Revises: 0019_wiilog_reconciliations
"""
from alembic import op
import sqlalchemy as sa


revision = "0020_tienda_reconciliations"
down_revision = "0019_wiilog_reconciliations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No backfill: las cargas históricas no registran qué pareja se ejecutó junta.
    op.create_table(
        "tienda_reconciliations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("periodo_id", sa.Integer(), nullable=False),
        sa.Column("wallet_email", sa.String(length=320), nullable=False),
        sa.Column("carga_ordenes_id", sa.Integer(), nullable=False),
        sa.Column("carga_wallet_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("creado_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["periodo_id"], ["periodos.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["carga_ordenes_id"], ["cargas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["carga_wallet_id"], ["cargas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "periodo_id", "carga_ordenes_id", "carga_wallet_id",
            name="uq_tienda_reconciliations_pair",
        ),
    )
    op.create_index(
        "ix_tienda_reconciliations_periodo_wallet_id",
        "tienda_reconciliations",
        ["periodo_id", "wallet_email", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tienda_reconciliations_periodo_wallet_id",
        table_name="tienda_reconciliations",
    )
    op.drop_table("tienda_reconciliations")
