"""Revisión y decisión de incidencias sin efectos financieros.

Revision ID: 0030_wallets_revision
Revises: 0029_wallets_tardios
"""
from alembic import op
import sqlalchemy as sa

revision = "0030_wallets_revision"
down_revision = "0029_wallets_tardios"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "wallets_tardios_revisiones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("movimiento_id", sa.Integer(), sa.ForeignKey("wallets_movimientos_tardios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("revisado_por", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("revisado_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("conclusion", sa.String(32), nullable=False),
        sa.Column("justificacion", sa.Text(), nullable=False),
        sa.Column("evidencia_revision", sa.String(512), nullable=False),
        sa.Column("autorizado_por", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("autorizado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision", sa.String(32), nullable=True),
        sa.Column("justificacion_decision", sa.Text(), nullable=True),
        sa.CheckConstraint("conclusion IN ('REQUIERE_CORRECCION','SIN_IMPACTO')", name="ck_wallets_tardios_conclusion"),
        sa.CheckConstraint("decision IS NULL OR decision IN ('AUTORIZAR_GESTION','RECHAZAR_GESTION')", name="ck_wallets_tardios_decision"),
        sa.UniqueConstraint("movimiento_id", name="uq_wallets_tardios_revision_movimiento"),
    )

def downgrade() -> None:
    op.drop_table("wallets_tardios_revisiones")
