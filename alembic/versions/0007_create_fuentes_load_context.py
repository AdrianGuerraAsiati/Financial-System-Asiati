"""create fuentes and add load context

Revision ID: 0007_create_fuentes_load_context
Revises: 0006_create_hallazgos
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_create_fuentes_load_context"
down_revision: Union[str, None] = "0006_create_hallazgos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fuentes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["empresa_id"],
            ["empresas.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fuentes_empresa_id",
        "fuentes",
        ["empresa_id"],
        unique=False,
    )

    op.add_column(
        "cargas",
        sa.Column("fuente_id", sa.Integer(), nullable=False),
    )
    op.add_column(
        "cargas",
        sa.Column("periodo_id", sa.Integer(), nullable=False),
    )
    op.create_foreign_key(
        "fk_cargas_fuente_id_fuentes",
        "cargas",
        "fuentes",
        ["fuente_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_cargas_periodo_id_periodos",
        "cargas",
        "periodos",
        ["periodo_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_cargas_periodo_id_periodos",
        "cargas",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_cargas_fuente_id_fuentes",
        "cargas",
        type_="foreignkey",
    )
    op.drop_column("cargas", "periodo_id")
    op.drop_column("cargas", "fuente_id")

    op.drop_index("ix_fuentes_empresa_id", table_name="fuentes")
    op.drop_table("fuentes")
