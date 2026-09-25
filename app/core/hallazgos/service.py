from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.hallazgos.model import Hallazgo


def hay_criticos_abiertos(hallazgos: Iterable[Hallazgo]) -> bool:
    """Indica si existe al menos un hallazgo crítico sin resolver."""
    return any(
        hallazgo.critico and not hallazgo.resuelto
        for hallazgo in hallazgos
    )


def existen_criticos_abiertos(session: Session, periodo_id: int) -> bool:
    """Consulta si el período tiene al menos un hallazgo crítico abierto."""
    statement = (
        select(Hallazgo.id)
        .where(
            Hallazgo.periodo_id == periodo_id,
            Hallazgo.critico.is_(True),
            Hallazgo.resuelto.is_(False),
        )
        .limit(1)
    )
    return session.scalar(statement) is not None
