from typing import Any

from sqlalchemy.orm import Session

from app.core.auditoria.model import Auditoria


def registrar_auditoria(
    session: Session,
    *,
    usuario_id: int | None,
    accion: str,
    entidad: str,
    entidad_id: int | None,
    empresa_id: int | None = None,
    antes: dict[str, Any] | None = None,
    despues: dict[str, Any] | None = None,
    ip: str | None = None,
) -> Auditoria:
    """Agrega la fila de auditoría a la misma transacción que la acción."""
    fila = Auditoria(
        usuario_id=usuario_id,
        empresa_id=empresa_id,
        accion=accion,
        entidad=entidad,
        entidad_id=entidad_id,
        antes=antes,
        despues=despues,
        ip=ip,
    )
    session.add(fila)
    return fila
