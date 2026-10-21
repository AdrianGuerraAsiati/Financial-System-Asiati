"""Permitir comprobantes sin condición financiera, pendientes de asociación.

Revision ID: 0035_cartera_comprobante_simple
Revises: 0034_cartera_oc_drive
"""
from alembic import op
import sqlalchemy as sa

revision = "0035_cartera_comprobante_simple"
down_revision = "0034_cartera_oc_drive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for columna, tipo in (
        ("cliente", sa.String(length=255)),
        ("pais", sa.String(length=100)),
        ("comercial", sa.String(length=255)),
        ("monto_esperado", sa.Numeric(precision=18, scale=2)),
    ):
        op.alter_column(
            "cartera_comprobantes_pago",
            columna,
            existing_type=tipo,
            existing_nullable=False,
            nullable=True,
        )


def downgrade() -> None:
    conexion = op.get_bind()
    pendientes = conexion.scalar(sa.text(
        "SELECT count(*) FROM cartera_comprobantes_pago WHERE "
        "cliente IS NULL OR pais IS NULL OR comercial IS NULL OR monto_esperado IS NULL"
    ))
    if pendientes:
        raise RuntimeError(
            "Existen comprobantes pendientes de asociación. "
            "No se puede restaurar la restricción NOT NULL sin resolverlos."
        )
    for columna, tipo in (
        ("cliente", sa.String(length=255)),
        ("pais", sa.String(length=100)),
        ("comercial", sa.String(length=255)),
        ("monto_esperado", sa.Numeric(precision=18, scale=2)),
    ):
        op.alter_column(
            "cartera_comprobantes_pago",
            columna,
            existing_type=tipo,
            existing_nullable=True,
            nullable=False,
        )
