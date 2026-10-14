"""Ejecución única de reapertura con solicitud aprobada.

Revision ID: 0032_wallets_ejecucion
Revises: 0031_wallets_reapertura
"""
from alembic import op
import sqlalchemy as sa
revision = "0032_wallets_ejecucion"
down_revision = "0031_wallets_reapertura"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "wallets_ejecuciones_reapertura",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("empresa_id",sa.Integer(),sa.ForeignKey("empresas.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("periodo_id",sa.Integer(),sa.ForeignKey("periodos.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("solicitud_id",sa.Integer(),sa.ForeignKey("wallets_solicitudes_reapertura.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("ejecutado_por",sa.Integer(),sa.ForeignKey("usuarios.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("ejecutado_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column("motivo",sa.Text(),nullable=False),
        sa.Column("plan_ref",sa.String(512),nullable=False),
        sa.Column("evidencia_previa_ref",sa.String(512),nullable=False),
        sa.ForeignKeyConstraint(["periodo_id","empresa_id"],["periodos.id","periodos.empresa_id"],name="fk_wallets_ejecucion_periodo_empresa",ondelete="RESTRICT"),
        sa.UniqueConstraint("solicitud_id",name="uq_wallets_ejecucion_solicitud"),
    )

def downgrade() -> None:
    op.drop_table("wallets_ejecuciones_reapertura")
