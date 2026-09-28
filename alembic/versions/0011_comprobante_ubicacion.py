"""add payment proof storage location

Revision ID: 0011_comprobante_ubicacion
Revises: 0010_cartera_comprobantes_pago
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011_comprobante_ubicacion"
down_revision: Union[str, None] = "0010_cartera_comprobantes_pago"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cartera_comprobantes_pago",
        sa.Column("ubicacion_archivo", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cartera_comprobantes_pago", "ubicacion_archivo")
