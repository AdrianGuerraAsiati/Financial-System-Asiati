"""create period close audit history

Revision ID: 0005_create_period_close_history
Revises: 0004_add_period_close_state
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_create_period_close_history"
down_revision: Union[str, None] = "0004_add_period_close_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "periodo_cierre_eventos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("periodo_id", sa.Integer(), nullable=False),
        sa.Column("accion", sa.String(length=16), nullable=False),
        sa.Column("estado_anterior", sa.Boolean(), nullable=False),
        sa.Column("estado_nuevo", sa.Boolean(), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column(
            "ocurrido_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
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
        "ix_periodo_cierre_eventos_periodo_id",
        "periodo_cierre_eventos",
        ["periodo_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_periodo_cierre_eventos_periodo_id",
        table_name="periodo_cierre_eventos",
    )
    op.drop_table("periodo_cierre_eventos")
