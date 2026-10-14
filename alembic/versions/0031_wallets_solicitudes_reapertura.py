"""Solicitudes controladas para reapertura, sin efectuar operaciones financieras.

Revision ID: 0031_wallets_reapertura
Revises: 0030_wallets_revision
"""
from alembic import op
import sqlalchemy as sa

revision = "0031_wallets_reapertura"
down_revision = "0030_wallets_revision"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "wallets_solicitudes_reapertura",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("periodo_id", sa.Integer(), sa.ForeignKey("periodos.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("revision_id", sa.Integer(), sa.ForeignKey("wallets_tardios_revisiones.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("solicitado_por", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("solicitado_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("evidencia_ref", sa.String(512), nullable=False),
        sa.Column("decision", sa.String(16), nullable=True),
        sa.Column("decidido_por", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("decidido_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_decision", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["periodo_id", "empresa_id"], ["periodos.id", "periodos.empresa_id"], name="fk_wallets_solicitud_periodo_empresa", ondelete="RESTRICT"),
        sa.UniqueConstraint("revision_id", name="uq_wallets_solicitud_revision"),
        sa.CheckConstraint("decision IS NULL OR decision IN ('APROBADA','RECHAZADA')", name="ck_wallets_solicitud_decision"),
    )

def downgrade() -> None:
    op.drop_table("wallets_solicitudes_reapertura")
