"""auditable snapshots for Compras / Supply Chain

Revision ID: 0014_compras_snapshots
Revises: 0013_usuarios_auth_auditoria
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0014_compras_snapshots"
down_revision: Union[str, None] = "0013_usuarios_auth_auditoria"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "compras_snapshots",
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
        sa.Column("lineas", sa.Integer(), nullable=False),
        sa.Column("esquema_valido", sa.Boolean(), nullable=False),
        sa.Column(
            "rangos_por_pais",
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
            name="uq_compras_snapshots_empresa_hash",
        ),
    )
    op.create_index(
        "ix_compras_snapshots_empresa_id",
        "compras_snapshots",
        ["empresa_id"],
    )
    op.create_index(
        "ix_compras_snapshots_guardado_en",
        "compras_snapshots",
        ["guardado_en"],
    )

    op.create_table(
        "compras_snapshot_lineas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("pais", sa.String(length=2), nullable=False),
        sa.Column("hoja_fuente", sa.String(length=255), nullable=False),
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
            ["compras_snapshots.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_id",
            "pais",
            "fila_fuente",
            name="uq_compras_snapshot_linea_fuente",
        ),
    )
    op.create_index(
        "ix_compras_snapshot_lineas_snapshot_id",
        "compras_snapshot_lineas",
        ["snapshot_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_compras_snapshot_lineas_snapshot_id",
        table_name="compras_snapshot_lineas",
    )
    op.drop_table("compras_snapshot_lineas")

    op.drop_index(
        "ix_compras_snapshots_guardado_en",
        table_name="compras_snapshots",
    )
    op.drop_index(
        "ix_compras_snapshots_empresa_id",
        table_name="compras_snapshots",
    )
    op.drop_table("compras_snapshots")
