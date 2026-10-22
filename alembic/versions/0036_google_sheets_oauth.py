"""Conexiones OAuth de Google Sheets por empresa y solicitudes PKCE de un solo uso.

Revision ID: 0036_google_sheets_oauth
Revises: 0035_cartera_comprobante_simple
"""
from alembic import op
import sqlalchemy as sa

revision = "0036_google_sheets_oauth"
down_revision = "0035_cartera_comprobante_simple"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "google_sheets_oauth_conexiones",
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("refresh_token_cifrado", sa.Text(), nullable=False),
        sa.Column("autorizado_por", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "google_sheets_oauth_estados",
        sa.Column("state_hash", sa.String(64), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_verifier", sa.String(128), nullable=False),
        sa.Column("vence_en", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_google_sheets_oauth_estados_vence_en", "google_sheets_oauth_estados", ["vence_en"])


def downgrade() -> None:
    op.drop_index("ix_google_sheets_oauth_estados_vence_en", table_name="google_sheets_oauth_estados")
    op.drop_table("google_sheets_oauth_estados")
    op.drop_table("google_sheets_oauth_conexiones")
