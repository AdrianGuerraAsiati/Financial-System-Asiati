"""administrable value lists for the 7 categorization dimensions

Revision ID: 0018_dimension_valores
Revises: 0017_hallazgos_clave_estable
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0018_dimension_valores"
down_revision: Union[str, None] = "0017_hallazgos_clave_estable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dimension_valores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dimension", sa.String(length=32), nullable=False),
        sa.Column("valor", sa.String(length=120), nullable=False),
        sa.Column("valor_normalizado", sa.String(length=120), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("creado_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "dimension IN ('ingreso_egreso', 'unidad_negocio', 'categoria', 'empresa', 'fijo_variable')",
            name="ck_dimension_valores_dimension",
        ),
        sa.UniqueConstraint("dimension", "valor_normalizado", name="uq_dimension_valores_normalizado"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dimension_valores_dimension", "dimension_valores", ["dimension"])


def downgrade() -> None:
    op.drop_index("ix_dimension_valores_dimension", table_name="dimension_valores")
    op.drop_table("dimension_valores")
