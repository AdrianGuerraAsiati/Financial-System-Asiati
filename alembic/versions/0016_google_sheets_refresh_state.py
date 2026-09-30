"""debounced Google Sheets source refresh state

Revision ID: 0016_google_sheets_refresh_state
Revises: 0015_cartera_snapshots
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0016_google_sheets_refresh_state"
down_revision: Union[str, None] = "0015_cartera_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "source_refresh_states",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("modulo", sa.String(length=32), nullable=False),
        sa.Column(
            "estado",
            sa.String(length=16),
            server_default="IDLE",
            nullable=False,
        ),
        sa.Column("first_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_through_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_refresh_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "estado IN ('IDLE', 'PENDING', 'REFRESHING', 'ERROR')",
            name="ck_source_refresh_states_estado",
        ),
        sa.CheckConstraint(
            "modulo IN ('cartera', 'compras')",
            name="ck_source_refresh_states_modulo",
        ),
        sa.ForeignKeyConstraint(
            ["empresa_id"],
            ["empresas.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "empresa_id",
            "modulo",
            name="uq_source_refresh_states_empresa_modulo",
        ),
    )
    op.create_index(
        "ix_source_refresh_states_empresa_id",
        "source_refresh_states",
        ["empresa_id"],
    )
    op.create_index(
        "ix_source_refresh_states_estado",
        "source_refresh_states",
        ["estado"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_source_refresh_states_estado",
        table_name="source_refresh_states",
    )
    op.drop_index(
        "ix_source_refresh_states_empresa_id",
        table_name="source_refresh_states",
    )
    op.drop_table("source_refresh_states")
