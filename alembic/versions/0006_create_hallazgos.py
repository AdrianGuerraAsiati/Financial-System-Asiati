"""create hallazgos

Revision ID: 0006_create_hallazgos
Revises: 0005_create_period_close_history
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_create_hallazgos"
down_revision: Union[str, None] = "0005_create_period_close_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hallazgos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("periodo_id", sa.Integer(), nullable=False),
        sa.Column(
            "critico",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "resuelto",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["periodo_id"],
            ["periodos.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_hallazgos_periodo_id",
        "hallazgos",
        ["periodo_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_hallazgos_periodo_id", table_name="hallazgos")
    op.drop_table("hallazgos")
