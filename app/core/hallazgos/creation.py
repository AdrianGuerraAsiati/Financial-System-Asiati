from typing import Any

from sqlalchemy.orm import Session

from app.core.hallazgos.model import Hallazgo


def registrar_hallazgo_motor(
    session: Session,
    *,
    periodo_id: int,
    motor_slug: str,
    codigo_regla: str,
    descripcion: str,
    evidencia: dict[str, Any],
    critico: bool,
) -> Hallazgo:
    """Registra un hallazgo de motor con explicación y evidencia estructurada."""
    hallazgo = Hallazgo(
        periodo_id=periodo_id,
        motor_slug=motor_slug,
        codigo_regla=codigo_regla,
        descripcion=descripcion,
        evidencia=evidencia,
        critico=critico,
        resuelto=False,
    )
    session.add(hallazgo)
    return hallazgo
