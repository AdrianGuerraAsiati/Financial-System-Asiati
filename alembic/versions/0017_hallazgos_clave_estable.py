"""stable key for motor findings and system notes

Revision ID: 0017_hallazgos_clave_estable
Revises: 0016_google_sheets_refresh_state
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0017_hallazgos_clave_estable"
down_revision: Union[str, None] = "0016_google_sheets_refresh_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clave estable del hallazgo dentro de (período, motor): reconciliar actualiza en vez de duplicar.
    op.add_column("hallazgos", sa.Column("clave", sa.String(length=300), nullable=True))
    op.add_column(
        "hallazgos",
        sa.Column(
            "resuelto_por_sistema",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    op.create_index(
        "uq_hallazgos_periodo_motor_clave",
        "hallazgos",
        ["periodo_id", "motor_slug", "clave"],
        unique=True,
        postgresql_where=sa.text("clave IS NOT NULL"),
    )
    op.drop_constraint("ck_hallazgo_mensajes_tipo", "hallazgo_mensajes", type_="check")
    op.create_check_constraint(
        "ck_hallazgo_mensajes_tipo",
        "hallazgo_mensajes",
        "tipo IN ('PREGUNTA', 'RESPUESTA', 'NOTA', 'SISTEMA')",
    )


def downgrade() -> None:
    op.execute("DELETE FROM hallazgo_mensajes WHERE tipo = 'SISTEMA'")
    op.drop_constraint("ck_hallazgo_mensajes_tipo", "hallazgo_mensajes", type_="check")
    op.create_check_constraint(
        "ck_hallazgo_mensajes_tipo",
        "hallazgo_mensajes",
        "tipo IN ('PREGUNTA', 'RESPUESTA', 'NOTA')",
    )
    op.drop_index("uq_hallazgos_periodo_motor_clave", table_name="hallazgos")
    op.drop_column("hallazgos", "resuelto_por_sistema")
    op.drop_column("hallazgos", "clave")
