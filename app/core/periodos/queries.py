from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.periodos.model import Periodo


def pertenece_a_empresa(
    session: Session,
    periodo_id: int,
    empresa_id: int,
) -> bool:
    """Indica si el período pertenece a la empresa indicada."""
    statement = select(Periodo.id).where(
        Periodo.id == periodo_id,
        Periodo.empresa_id == empresa_id,
    )
    return session.scalar(statement) is not None
