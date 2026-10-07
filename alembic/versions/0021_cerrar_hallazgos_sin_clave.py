"""Close wallet findings created before the stable key.

Revision ID: 0021_cerrar_hallazgos_sin_clave
Revises: 0020_tienda_reconciliations

Decisión 0008 (Juan Felipe Parra): los hallazgos del motor de wallets sin clave estable quedan CERRADOS con nota
automática "Reemplazado por el hallazgo con clave estable.". No se borra nada. No se cierran los que tienen trabajo
de una persona (mensajes o categorización): se listan con `python -m app.core.hallazgos.sin_clave`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0021_cerrar_hallazgos_sin_clave"
down_revision: Union[str, None] = "0020_tienda_reconciliations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ACCION = "hallazgo.cerrar_sin_clave"
NOTA = "Reemplazado por el hallazgo con clave estable."

CANDIDATOS = """
    SELECT h.id, h.estado, h.resuelto, p.empresa_id
    FROM hallazgos h
    JOIN periodos p ON p.id = h.periodo_id
    WHERE h.motor_slug = 'conciliacion_wallets'
      AND h.clave IS NULL
      AND h.estado <> 'cerrado'
      AND NOT (COALESCE(h.evidencia, '{}'::jsonb) ? 'categorizacion')
      AND NOT EXISTS (
          SELECT 1 FROM hallazgo_mensajes m
          WHERE m.hallazgo_id = h.id AND m.tipo <> 'SISTEMA'
      )
"""


def upgrade() -> None:
    # La nota automática de una migración no tiene usuario; solo se permite en mensajes SISTEMA.
    op.alter_column("hallazgo_mensajes", "usuario_id", existing_type=sa.Integer(), nullable=True)
    op.create_check_constraint(
        "ck_hallazgo_mensajes_usuario",
        "hallazgo_mensajes",
        "usuario_id IS NOT NULL OR tipo = 'SISTEMA'",
    )
    op.execute(
        sa.text(
            f"""
            WITH candidatos AS ({CANDIDATOS}),
            auditados AS (
                INSERT INTO auditoria (usuario_id, empresa_id, accion, entidad, entidad_id, antes, despues)
                SELECT NULL, c.empresa_id, :accion, 'hallazgo', c.id,
                       jsonb_build_object('estado', c.estado, 'resuelto', c.resuelto),
                       jsonb_build_object('estado', 'cerrado', 'resuelto', true, 'nota', CAST(:nota AS text))
                FROM candidatos c
                RETURNING entidad_id
            ),
            notas AS (
                INSERT INTO hallazgo_mensajes (hallazgo_id, usuario_id, tipo, texto)
                SELECT entidad_id, NULL, 'SISTEMA', :nota FROM auditados
                RETURNING hallazgo_id
            )
            UPDATE hallazgos SET estado = 'cerrado', resuelto = true
            WHERE id IN (SELECT hallazgo_id FROM notas)
            """
        ).bindparams(accion=ACCION, nota=NOTA)
    )


def downgrade() -> None:
    # Restaura únicamente lo creado por esta migración. No borra otros mensajes SISTEMA sin autor.
    op.execute(
        sa.text(
            """
            UPDATE hallazgos h
            SET estado = a.antes->>'estado', resuelto = (a.antes->>'resuelto')::boolean
            FROM auditoria a
            WHERE a.accion = :accion AND a.entidad = 'hallazgo' AND a.entidad_id = h.id
            """
        ).bindparams(accion=ACCION)
    )
    op.execute(
        sa.text(
            """
            DELETE FROM hallazgo_mensajes m
            USING auditoria a
            WHERE a.accion = :accion
              AND a.entidad = 'hallazgo'
              AND a.entidad_id = m.hallazgo_id
              AND m.usuario_id IS NULL
              AND m.tipo = 'SISTEMA'
              AND m.texto = :nota
            """
        ).bindparams(accion=ACCION, nota=NOTA)
    )
    op.execute(sa.text("DELETE FROM auditoria WHERE accion = :accion").bindparams(accion=ACCION))
    op.drop_constraint("ck_hallazgo_mensajes_usuario", "hallazgo_mensajes", type_="check")
    op.alter_column("hallazgo_mensajes", "usuario_id", existing_type=sa.Integer(), nullable=False)
