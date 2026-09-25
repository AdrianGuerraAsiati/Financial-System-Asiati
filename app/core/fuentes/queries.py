from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.fuentes.model import Fuente


def pertenece_a_empresa(
    session: Session,
    fuente_id: int,
    empresa_id: int,
) -> bool:
    """Indica si la fuente pertenece a la empresa indicada."""
    statement = select(Fuente.id).where(
        Fuente.id == fuente_id,
        Fuente.empresa_id == empresa_id,
    )
    return session.scalar(statement) is not None
