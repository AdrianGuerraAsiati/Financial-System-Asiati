from collections.abc import Iterable

from app.core.hallazgos.model import Hallazgo


def hay_criticos_abiertos(hallazgos: Iterable[Hallazgo]) -> bool:
    """Indica si existe al menos un hallazgo crítico sin resolver."""
    return any(
        hallazgo.critico and not hallazgo.resuelto
        for hallazgo in hallazgos
    )
