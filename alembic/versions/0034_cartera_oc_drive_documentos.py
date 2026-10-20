"""Inventario de revisiones de O.C. desde Drive, sin atribución jurídica.

Revision ID: 0034_cartera_oc_drive
Revises: 0033_wallets_correccion
"""
from alembic import op
import sqlalchemy as sa

revision = "0034_cartera_oc_drive"
down_revision = "0033_wallets_correccion"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cartera_oc_drive_documentos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("drive_file_id", sa.String(150), nullable=False),
        sa.Column("drive_version", sa.String(80), nullable=False),
        sa.Column("nombre_original", sa.String(500), nullable=False),
        sa.Column("ruta_carpetas", sa.String(1800), nullable=False),
        sa.Column("mime_type", sa.String(160), nullable=False),
        sa.Column("modificado_drive", sa.String(80), nullable=True),
        sa.Column("numero_oc_candidato", sa.String(80), nullable=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("estado", sa.String(32), nullable=False, server_default="SIN_ASIGNAR"),
        sa.Column("visto_primera_vez", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("visto_ultima_vez", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("drive_file_id", "drive_version", name="uq_cartera_oc_drive_revision"),
    )
    op.create_index("ix_cartera_oc_drive_numero", "cartera_oc_drive_documentos", ["numero_oc_candidato"])


def downgrade():
    op.drop_index("ix_cartera_oc_drive_numero", table_name="cartera_oc_drive_documentos")
    op.drop_table("cartera_oc_drive_documentos")
