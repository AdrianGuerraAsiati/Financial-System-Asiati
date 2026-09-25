from sqlalchemy.orm import Session

from app.core.hallazgos import Hallazgo, registrar_hallazgo_motor
from app.core.motor import Resultado


MOTOR_SLUG = "conciliacion_wallets"


def registrar_resultado(
    session: Session,
    *,
    periodo_id: int,
    resultado: Resultado,
) -> Hallazgo:
    """Convierte un resultado puro de Wallets en un hallazgo explicable."""
    return registrar_hallazgo_motor(
        session,
        periodo_id=periodo_id,
        motor_slug=MOTOR_SLUG,
        codigo_regla=resultado.codigo,
        descripcion=resultado.descripcion,
        evidencia=resultado.datos,
        critico=resultado.critico,
    )
