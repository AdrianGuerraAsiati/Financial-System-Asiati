from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.motores.cartera_ocs.comprobantes import ESTADOS_AUDITORIA_PENDIENTES
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
            ComprobantePagoPersistido.estado_auditoria.in_(ESTADOS_AUDITORIA_PENDIENTES),
        )
        .order_by(ComprobantePagoPersistido.id.asc())
    )

    return tuple(session.scalars(statement).all())


def contar_comprobantes_pendientes(
    session: Session,
    *,
    empresa_id: int,
    oc: str,
) -> int:
    """Cuenta soportes pendientes de una OC sin acoplar el detalle al modelo SQL."""
    statement = select(func.count(ComprobantePagoPersistido.id)).where(
        ComprobantePagoPersistido.empresa_id == empresa_id,
        ComprobantePagoPersistido.oc == oc,
        ComprobantePagoPersistido.estado_auditoria.in_(ESTADOS_AUDITORIA_PENDIENTES),
    )
    return int(session.scalar(statement) or 0)
