"""auditable snapshots for Cartera

Revision ID: 0015_cartera_snapshots
Revises: 0014_compras_snapshots
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0015_cartera_snapshots"
down_revision: Union[str, None] = "0014_compras_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cartera_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("spreadsheet_id", sa.String(length=255), nullable=False),
        sa.Column("modo_fuente", sa.String(length=50), nullable=False),
        sa.Column("contenido_hash", sa.String(length=64), nullable=False),
        sa.Column("cargado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "guardado_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("filas", sa.Integer(), nullable=False),
        sa.Column("operaciones", sa.Integer(), nullable=False),
        sa.Column("registros_mora", sa.Integer(), nullable=False),
        sa.Column("proyecciones", sa.Integer(), nullable=False),
        sa.Column(
            "rangos",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "diagnosticos",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["empresa_id"],
            ["empresas.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "empresa_id",
            "contenido_hash",
            name="uq_cartera_snapshots_empresa_hash",
        ),
    )
    op.create_index(
        "ix_cartera_snapshots_empresa_id",
        "cartera_snapshots",
        ["empresa_id"],
    )
    op.create_index(
        "ix_cartera_snapshots_guardado_en",
        "cartera_snapshots",
        ["guardado_en"],
    )

    op.create_table(
        "cartera_snapshot_filas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("fila_fuente", sa.Integer(), nullable=False),
        sa.Column(
            "crudo",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "normalizado",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["cartera_snapshots.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_id",
            "tipo",
            "fila_fuente",
            name="uq_cartera_snapshot_fila_fuente",
        ),
    )
    op.create_index(
        "ix_cartera_snapshot_filas_snapshot_id",
        "cartera_snapshot_filas",
        ["snapshot_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cartera_snapshot_filas_snapshot_id",
        table_name="cartera_snapshot_filas",
    )
    op.drop_table("cartera_snapshot_filas")

    op.drop_index(
        "ix_cartera_snapshots_guardado_en",
        table_name="cartera_snapshots",
    )
    op.drop_index(
        "ix_cartera_snapshots_empresa_id",
        table_name="cartera_snapshots",
    )
    op.drop_table("cartera_snapshots")
