from sqlalchemy import select
from sqlalchemy.orm import Session

from app.motores.cartera_ocs.persistencia import ComprobantePagoPersistido


def listar_comprobantes_pendientes(
    session: Session,
    *,
    empresa_id: int,
) -> tuple[ComprobantePagoPersistido, ...]:
    """Lista comprobantes pendientes de auditoría para una empresa."""
    statement = (
        select(ComprobantePagoPersistido)
        .where(
            ComprobantePagoPersistido.empresa_id == empresa_id,
            ComprobantePagoPersistido.estado_auditoria == "PENDIENTE",
        )
        .order_by(ComprobantePagoPersistido.id.asc())
    )

    return tuple(session.scalars(statement).all())
