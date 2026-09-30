"""core movimientos and categorization rules

Revision ID: 0017_movimientos_categorizacion
Revises: 0016_google_sheets_refresh_state
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0017_movimientos_categorizacion"
down_revision: Union[str, None] = "0016_google_sheets_refresh_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reglas_categorizacion",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("motor_slug", sa.String(length=100), nullable=False),
        sa.Column("fuente_id", sa.Integer(), nullable=True),
        sa.Column("patron", sa.Text(), nullable=False),
        sa.Column("tipo_match", sa.String(length=20), nullable=False),
        sa.Column("prioridad", sa.Integer(), nullable=False),
        sa.Column("condiciones", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tipo", sa.String(length=32), nullable=True),
        sa.Column("unidad_negocio", sa.String(length=255), nullable=True),
        sa.Column("categoria", sa.String(length=255), nullable=True),
        sa.Column("empresa", sa.String(length=255), nullable=True),
        sa.Column("tercero", sa.String(length=255), nullable=True),
        sa.Column("modalidad", sa.String(length=100), nullable=True),
        sa.Column("fijo_variable", sa.String(length=32), nullable=True),
        sa.Column("ciudad", sa.String(length=255), nullable=True),
        sa.Column(
            "requiere_revision",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("activa", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("origen", sa.String(length=100), nullable=True),
        sa.Column("veces_aplicada", sa.Integer(), server_default="0", nullable=False),
        sa.Column("creado_por", sa.Integer(), nullable=True),
        sa.Column(
            "creado_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "tipo_match IN ('EXACTO', 'EMPIEZA_CON', 'CONTIENE', 'REGEX')",
            name="ck_reglas_categorizacion_tipo_match",
        ),
        sa.ForeignKeyConstraint(["creado_por"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["fuente_id"], ["fuentes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_reglas_categorizacion_motor_slug",
        "reglas_categorizacion",
        ["motor_slug"],
    )
    op.create_index(
        "ix_reglas_categorizacion_fuente_id",
        "reglas_categorizacion",
        ["fuente_id"],
    )

    op.create_table(
        "movimientos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("fuente_id", sa.Integer(), nullable=False),
        sa.Column("carga_id", sa.Integer(), nullable=False),
        sa.Column("periodo_id", sa.Integer(), nullable=False),
        sa.Column("fecha_pago_oportuno", sa.Date(), nullable=True),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=True),
        sa.Column("monto", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("ciudad", sa.String(length=255), nullable=True),
        sa.Column("unidad_negocio", sa.String(length=255), nullable=True),
        sa.Column("categoria", sa.String(length=255), nullable=True),
        sa.Column("empresa", sa.String(length=255), nullable=True),
        sa.Column("tercero", sa.String(length=255), nullable=True),
        sa.Column("modalidad", sa.String(length=100), nullable=True),
        sa.Column("fijo_variable", sa.String(length=32), nullable=True),
        sa.Column("recibo_pago_caja", sa.Text(), nullable=True),
        sa.Column("causacion", sa.Text(), nullable=True),
        sa.Column("descripcion_norm", sa.Text(), nullable=False),
        sa.Column(
            "estado_categoria",
            sa.String(length=16),
            server_default="PENDIENTE",
            nullable=False,
        ),
        sa.Column("regla_id", sa.Integer(), nullable=True),
        sa.Column("categorizado_por", sa.Integer(), nullable=True),
        sa.Column("categorizado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("referencia_externa", sa.String(length=255), nullable=True),
        sa.Column("hash_fila", sa.String(length=64), nullable=False),
        sa.Column("crudo", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "estado_categoria IN ('AUTO', 'REVISAR', 'PENDIENTE', 'MANUAL')",
            name="ck_movimientos_estado_categoria",
        ),
        sa.ForeignKeyConstraint(["carga_id"], ["cargas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["categorizado_por"], ["usuarios.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["fuente_id"], ["fuentes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["periodo_id"], ["periodos.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["regla_id"], ["reglas_categorizacion.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "carga_id",
            "hash_fila",
            name="uq_movimientos_carga_hash_fila",
        ),
    )
    op.create_index("ix_movimientos_fuente_id", "movimientos", ["fuente_id"])
    op.create_index("ix_movimientos_carga_id", "movimientos", ["carga_id"])
    op.create_index("ix_movimientos_periodo_id", "movimientos", ["periodo_id"])
    op.create_index(
        "ix_movimientos_estado_categoria",
        "movimientos",
        ["estado_categoria"],
    )
    op.create_index("ix_movimientos_regla_id", "movimientos", ["regla_id"])


def downgrade() -> None:
    op.drop_index("ix_movimientos_regla_id", table_name="movimientos")
    op.drop_index("ix_movimientos_estado_categoria", table_name="movimientos")
    op.drop_index("ix_movimientos_periodo_id", table_name="movimientos")
    op.drop_index("ix_movimientos_carga_id", table_name="movimientos")
    op.drop_index("ix_movimientos_fuente_id", table_name="movimientos")
    op.drop_table("movimientos")

    op.drop_index(
        "ix_reglas_categorizacion_fuente_id",
        table_name="reglas_categorizacion",
    )
    op.drop_index(
        "ix_reglas_categorizacion_motor_slug",
        table_name="reglas_categorizacion",
    )
    op.drop_table("reglas_categorizacion")
