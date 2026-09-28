"""create usuarios with first-version roles

Revision ID: 0009_create_usuarios_roles
Revises: 0008_hallazgos_explainability
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009_create_usuarios_roles"
down_revision: Union[str, None] = "0008_hallazgos_explainability"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("rol", sa.String(length=64), nullable=False),
        sa.Column(
            "activo",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("usuarios")
