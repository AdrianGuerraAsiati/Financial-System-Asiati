"""Expedientes de propuestas de corrección, sin aplicar ajustes.

Revision ID: 0033_wallets_correccion
Revises: 0032_wallets_ejecucion
"""
from alembic import op
import sqlalchemy as sa
revision="0033_wallets_correccion"
down_revision="0032_wallets_ejecucion"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("wallets_expedientes_correccion",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("empresa_id",sa.Integer(),sa.ForeignKey("empresas.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("periodo_id",sa.Integer(),sa.ForeignKey("periodos.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("ejecucion_id",sa.Integer(),sa.ForeignKey("wallets_ejecuciones_reapertura.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("carga_id",sa.Integer(),sa.ForeignKey("cargas.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("movimiento_ref",sa.String(320),nullable=False),
        sa.Column("valor_anterior",sa.Numeric(20,2),nullable=False),
        sa.Column("valor_propuesto",sa.Numeric(20,2),nullable=False),
        sa.Column("evidencia_antes_ref",sa.String(512),nullable=False),
        sa.Column("evidencia_despues_ref",sa.String(512),nullable=False),
        sa.Column("justificacion",sa.Text(),nullable=False),
        sa.Column("preparado_por",sa.Integer(),sa.ForeignKey("usuarios.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("preparado_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column("decision",sa.String(24),nullable=True),
        sa.Column("decidido_por",sa.Integer(),sa.ForeignKey("usuarios.id",ondelete="RESTRICT"),nullable=True),
        sa.Column("decidido_at",sa.DateTime(timezone=True),nullable=True),
        sa.Column("motivo_decision",sa.Text(),nullable=True),
        sa.ForeignKeyConstraint(["periodo_id","empresa_id"],["periodos.id","periodos.empresa_id"],name="fk_wallets_expediente_periodo_empresa",ondelete="RESTRICT"),
        sa.UniqueConstraint("ejecucion_id","carga_id","movimiento_ref",name="uq_wallets_expediente_movimiento"),
        sa.CheckConstraint("decision IS NULL OR decision IN ('AUTORIZAR_EJECUCION','RECHAZAR')",name="ck_wallets_expediente_decision"),
    )

def downgrade():
    op.drop_table("wallets_expedientes_correccion")
