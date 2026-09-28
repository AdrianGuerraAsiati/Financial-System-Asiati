"""persist cartera payment proofs

Revision ID: 0010_cartera_comprobantes_pago
Revises: 0009_create_usuarios_roles
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_cartera_comprobantes_pago"
down_revision: Union[str, None] = "0009_create_usuarios_roles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cartera_comprobantes_pago",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("oc", sa.String(length=120), nullable=False),
        sa.Column("cliente", sa.String(length=255), nullable=False),
        sa.Column("pais", sa.String(length=100), nullable=False),
        sa.Column("comercial", sa.String(length=255), nullable=False),
        sa.Column("monto_esperado", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("nombre_archivo", sa.String(length=255), nullable=False),
        sa.Column("contenido_hash", sa.String(length=64), nullable=False),
        sa.Column("estado_auditoria", sa.String(length=40), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["empresa_id"],
            ["empresas.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cartera_comprobantes_pago_empresa_id",
        "cartera_comprobantes_pago",
        ["empresa_id"],
        unique=False,
    )
    op.create_index(
        "ix_cartera_comprobantes_pago_oc",
        "cartera_comprobantes_pago",
        ["oc"],
        unique=False,
    )
    op.create_index(
        "ix_cartera_comprobantes_pago_estado_auditoria",
        "cartera_comprobantes_pago",
        ["estado_auditoria"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cartera_comprobantes_pago_estado_auditoria",
        table_name="cartera_comprobantes_pago",
    )
    op.drop_index(
        "ix_cartera_comprobantes_pago_oc",
        table_name="cartera_comprobantes_pago",
    )
    op.drop_index(
        "ix_cartera_comprobantes_pago_empresa_id",
        table_name="cartera_comprobantes_pago",
    )
    op.drop_table("cartera_comprobantes_pago")
