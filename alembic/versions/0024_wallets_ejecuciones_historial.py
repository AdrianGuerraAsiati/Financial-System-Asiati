"""Historial inmutable de respuestas de conciliación Wallets.

Revision ID: 0024_wallets_historial
Revises: 0023_recaudos_reportados
"""
from alembic import op
import sqlalchemy as sa

revision = "0024_wallets_historial"
down_revision = "0023_recaudos_reportados"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wallets_ejecuciones_historial",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("periodo_id", sa.Integer(), sa.ForeignKey("periodos.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tipo_wallet", sa.String(16), nullable=False),
        sa.Column("identidad_wallet", sa.String(320), nullable=True),
        sa.Column("carga_wallet_id", sa.Integer(), sa.ForeignKey("cargas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("carga_ordenes_id", sa.Integer(), sa.ForeignKey("cargas.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("bloqueado", sa.Boolean(), nullable=False),
        sa.Column("resultado", sa.JSON(), nullable=False),
        sa.Column("creado_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("tipo_wallet IN ('wiilog', 'tienda', 'pagos')", name="ck_wallets_historial_tipo"),
    )
    op.create_index("ix_wallets_historial_contexto", "wallets_ejecuciones_historial",
                    ["empresa_id", "periodo_id", "tipo_wallet", "id"])


def downgrade() -> None:
    op.drop_index("ix_wallets_historial_contexto", table_name="wallets_ejecuciones_historial")
    op.drop_table("wallets_ejecuciones_historial")
