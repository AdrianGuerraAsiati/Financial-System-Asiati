"""prevent duplicate payment proof content

Revision ID: 0012_comprobante_hash_unique
Revises: 0011_comprobante_ubicacion
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0012_comprobante_hash_unique"
down_revision: Union[str, None] = "0011_comprobante_ubicacion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_cartera_comprobante_empresa_hash",
        "cartera_comprobantes_pago",
        ["empresa_id", "contenido_hash"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_cartera_comprobante_empresa_hash",
        "cartera_comprobantes_pago",
        type_="unique",
    )
