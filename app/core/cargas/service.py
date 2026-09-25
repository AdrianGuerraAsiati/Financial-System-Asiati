from collections.abc import Callable

from sqlalchemy.orm import Session

from app.core.cargas.errors import ContextoCargaInvalidoError
from app.core.cargas.model import Carga
from app.core.fuentes import pertenece_a_empresa as fuente_pertenece_a_empresa
from app.core.periodos import pertenece_a_empresa as periodo_pertenece_a_empresa


ValidadorPertenencia = Callable[[Session, int, int], bool]


def registrar_carga(
    session: Session,
    *,
    empresa_id: int,
    fuente_id: int,
    periodo_id: int,
    contenido_hash: str,
    fuente_pertenece: ValidadorPertenencia = fuente_pertenece_a_empresa,
    periodo_pertenece: ValidadorPertenencia = periodo_pertenece_a_empresa,
) -> Carga:
    """Registra una carga únicamente dentro de un contexto empresarial coherente."""
    if not fuente_pertenece(session, fuente_id, empresa_id):
        raise ContextoCargaInvalidoError(
            "La fuente no pertenece a la empresa de la carga."
        )

    if not periodo_pertenece(session, periodo_id, empresa_id):
        raise ContextoCargaInvalidoError(
            "El período no pertenece a la empresa de la carga."
        )

    carga = Carga(
        empresa_id=empresa_id,
        fuente_id=fuente_id,
        periodo_id=periodo_id,
        contenido_hash=contenido_hash,
    )
    session.add(carga)
    return carga
