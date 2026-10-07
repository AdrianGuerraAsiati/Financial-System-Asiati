"""Track Wiilog file pairs and execution order independently of reusable loads.

Revision ID: 0019_wiilog_reconciliations
Revises: 0018_dimension_valores
"""
from alembic import op
import sqlalchemy as sa


revision = "0019_wiilog_reconciliations"
down_revision = "0018_dimension_valores"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No backfill: legacy loads/findings do not record which file pairs ran together.
    op.create_table(
        "wiilog_reconciliations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("periodo_id", sa.Integer(), nullable=False),
        sa.Column("carga_ordenes_id", sa.Integer(), nullable=False),
        sa.Column("carga_wallet_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("creado_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["periodo_id"], ["periodos.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["carga_ordenes_id"], ["cargas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["carga_wallet_id"], ["cargas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("periodo_id", "carga_ordenes_id", "carga_wallet_id",
                            name="uq_wiilog_reconciliations_pair"),
    )
    op.create_index("ix_wiilog_reconciliations_periodo_id", "wiilog_reconciliations", ["periodo_id", "id"])


def downgrade() -> None:
    op.drop_index("ix_wiilog_reconciliations_periodo_id", table_name="wiilog_reconciliations")
    op.drop_table("wiilog_reconciliations")
