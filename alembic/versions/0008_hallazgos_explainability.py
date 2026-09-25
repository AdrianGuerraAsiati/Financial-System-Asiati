"""add explainability to hallazgos

Revision ID: 0008_hallazgos_explainability
Revises: 0007_create_fuentes_load_context
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0008_hallazgos_explainability"
down_revision: Union[str, None] = "0007_create_fuentes_load_context"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "hallazgos",
        sa.Column("motor_slug", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "hallazgos",
        sa.Column("codigo_regla", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "hallazgos",
        sa.Column("descripcion", sa.Text(), nullable=True),
    )
    op.add_column(
        "hallazgos",
        sa.Column("evidencia", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hallazgos", "evidencia")
    op.drop_column("hallazgos", "descripcion")
    op.drop_column("hallazgos", "codigo_regla")
    op.drop_column("hallazgos", "motor_slug")
