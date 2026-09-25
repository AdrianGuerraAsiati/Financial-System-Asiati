"""add period close state

Revision ID: 0004_add_period_close_state
Revises: 0003_create_periodos
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_add_period_close_state"
down_revision: Union[str, None] = "0003_create_periodos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "periodos",
        sa.Column(
            "cerrado",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("periodos", "cerrado")
