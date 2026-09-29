"""users with login, assigned companies, logins, audit and finding threads

Revision ID: 0013_usuarios_auth_auditoria
Revises: 0012_comprobante_hash_unique
"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0013_usuarios_auth_auditoria"
down_revision: Union[str, None] = "0012_comprobante_hash_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ROLES = (
    "super_administrador",
    "coordinacion_financiera",
    "conciliacion",
    "analista_tesoreria",
    "ti",
)
ESTADOS_HALLAZGO = ("detectado", "en_gestion", "escalado", "resuelto", "cerrado")


def _en_lista(columna: str, valores: tuple[str, ...]) -> str:
    return f"{columna} IN ({', '.join(repr(v) for v in valores)})"


def _exigir_usuarios_vacia() -> None:
    if context.is_offline_mode():
        return
    filas = op.get_bind().execute(sa.text("SELECT count(*) FROM usuarios")).scalar_one()
    if filas:
        raise RuntimeError(
            f"La tabla usuarios tiene {filas} fila(s) del modelo de la migración "
            "0009, sin correo ni contraseña, y esta migración no puede inventarlos. "
            "Si son datos de prueba, bórralos con: DELETE FROM usuarios; y vuelve "
            "a correr alembic upgrade head. Si son usuarios reales, no borres nada "
            "y avisa al dueño del núcleo."
        )


def upgrade() -> None:
    _exigir_usuarios_vacia()

    op.add_column("usuarios", sa.Column("email", sa.String(length=255), nullable=False))
    op.add_column("usuarios", sa.Column("password_hash", sa.Text(), nullable=False))
    op.add_column(
        "usuarios",
        sa.Column(
            "debe_cambiar_password",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "usuarios",
        sa.Column("ultimo_ingreso_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("usuarios", sa.Column("creado_por", sa.Integer(), nullable=True))
    op.add_column(
        "usuarios",
        sa.Column(
            "creado_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_unique_constraint("uq_usuarios_email", "usuarios", ["email"])
    op.create_foreign_key(
        "fk_usuarios_creado_por",
        "usuarios",
        "usuarios",
        ["creado_por"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint("ck_usuarios_rol", "usuarios", _en_lista("rol", ROLES))

    op.create_table(
        "usuario_empresas",
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("asignado_por", sa.Integer(), nullable=True),
        sa.Column(
            "asignado_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["asignado_por"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("usuario_id", "empresa_id"),
    )
    op.create_index(
        "ix_usuario_empresas_empresa_id", "usuario_empresas", ["empresa_id"]
    )

    op.create_table(
        "ingresos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("email_intentado", sa.String(length=255), nullable=False),
        sa.Column("exito", sa.Boolean(), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "creado_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingresos_usuario_id", "ingresos", ["usuario_id"])
    op.create_index("ix_ingresos_creado_at", "ingresos", ["creado_at"])
    op.create_index(
        "ix_ingresos_email_creado_at", "ingresos", ["email_intentado", "creado_at"]
    )

    op.create_table(
        "auditoria",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("empresa_id", sa.Integer(), nullable=True),
        sa.Column("accion", sa.String(length=100), nullable=False),
        sa.Column("entidad", sa.String(length=100), nullable=False),
        sa.Column("entidad_id", sa.Integer(), nullable=True),
        sa.Column("antes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("despues", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column(
            "creado_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auditoria_usuario_id", "auditoria", ["usuario_id"])
    op.create_index("ix_auditoria_empresa_id", "auditoria", ["empresa_id"])
    op.create_index("ix_auditoria_creado_at", "auditoria", ["creado_at"])

    op.add_column(
        "hallazgos",
        sa.Column(
            "estado",
            sa.String(length=20),
            server_default="detectado",
            nullable=False,
        ),
    )
    op.execute("UPDATE hallazgos SET estado = 'resuelto' WHERE resuelto")
    op.create_check_constraint(
        "ck_hallazgos_estado", "hallazgos", _en_lista("estado", ESTADOS_HALLAZGO)
    )
    op.create_index("ix_hallazgos_estado", "hallazgos", ["estado"])

    op.create_table(
        "hallazgo_mensajes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("hallazgo_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=16), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column(
            "creado_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "tipo IN ('PREGUNTA', 'RESPUESTA', 'NOTA')",
            name="ck_hallazgo_mensajes_tipo",
        ),
        sa.ForeignKeyConstraint(["hallazgo_id"], ["hallazgos.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_hallazgo_mensajes_hallazgo_id", "hallazgo_mensajes", ["hallazgo_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_hallazgo_mensajes_hallazgo_id", table_name="hallazgo_mensajes")
    op.drop_table("hallazgo_mensajes")

    op.drop_index("ix_hallazgos_estado", table_name="hallazgos")
    op.drop_constraint("ck_hallazgos_estado", "hallazgos", type_="check")
    op.drop_column("hallazgos", "estado")

    op.drop_index("ix_auditoria_creado_at", table_name="auditoria")
    op.drop_index("ix_auditoria_empresa_id", table_name="auditoria")
    op.drop_index("ix_auditoria_usuario_id", table_name="auditoria")
    op.drop_table("auditoria")

    op.drop_index("ix_ingresos_email_creado_at", table_name="ingresos")
    op.drop_index("ix_ingresos_creado_at", table_name="ingresos")
    op.drop_index("ix_ingresos_usuario_id", table_name="ingresos")
    op.drop_table("ingresos")

    op.drop_index("ix_usuario_empresas_empresa_id", table_name="usuario_empresas")
    op.drop_table("usuario_empresas")

    op.drop_constraint("ck_usuarios_rol", "usuarios", type_="check")
    op.drop_constraint("fk_usuarios_creado_por", "usuarios", type_="foreignkey")
    op.drop_constraint("uq_usuarios_email", "usuarios", type_="unique")
    op.drop_column("usuarios", "creado_at")
    op.drop_column("usuarios", "creado_por")
    op.drop_column("usuarios", "ultimo_ingreso_at")
    op.drop_column("usuarios", "debe_cambiar_password")
    op.drop_column("usuarios", "password_hash")
    op.drop_column("usuarios", "email")
