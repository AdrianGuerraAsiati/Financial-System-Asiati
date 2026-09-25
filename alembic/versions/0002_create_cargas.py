"""create cargas

Revision ID: 0002_create_cargas
Revises: 0001_create_empresas
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_create_cargas"
down_revision: Union[str, None] = "0001_create_empresas"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cargas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("contenido_hash", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "empresa_id",
            "contenido_hash",
            name="uq_cargas_empresa_hash",
        ),
    )


def downgrade() -> None:
    op.drop_table("cargas")
