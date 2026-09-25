from datetime import date

from sqlalchemy.orm import Session

from app.core.periodos.errors import (
    MotivoReaperturaRequeridoError,
    PeriodoAbiertoError,
    PeriodoCerradoError,
)
from app.core.periodos.history import (
    ACCION_CERRAR,
    ACCION_REABRIR,
    PeriodoCierreEvento,
)
from app.core.periodos.model import Periodo


def actualizar_rango(
    periodo: Periodo,
    *,
    fecha_inicio: date,
    fecha_fin: date,
) -> None:
    """Actualiza el rango únicamente cuando el período está abierto."""
    if periodo.cerrado:
        raise PeriodoCerradoError("El período está cerrado y no puede modificarse.")

    periodo.fecha_inicio = fecha_inicio
    periodo.fecha_fin = fecha_fin


def cerrar_periodo(
    session: Session,
    periodo: Periodo,
    *,
    actor: str,
    motivo: str | None = None,
) -> PeriodoCierreEvento:
    """Cierra el período y registra la transición en la misma transacción."""
    if periodo.cerrado:
        raise PeriodoCerradoError("El período ya está cerrado.")

    evento = PeriodoCierreEvento(
        periodo_id=periodo.id,
        accion=ACCION_CERRAR,
        estado_anterior=False,
        estado_nuevo=True,
        actor=actor,
        motivo=motivo,
    )

    periodo.cerrado = True
    session.add(evento)
    return evento


def reabrir_periodo(
    session: Session,
    periodo: Periodo,
    *,
    actor: str,
    motivo: str,
) -> PeriodoCierreEvento:
    """Reabre un período cerrado dejando trazabilidad obligatoria."""
    if not periodo.cerrado:
        raise PeriodoAbiertoError("El período ya está abierto.")

    motivo_limpio = motivo.strip()
    if not motivo_limpio:
        raise MotivoReaperturaRequeridoError(
            "La reapertura requiere un motivo."
        )

    evento = PeriodoCierreEvento(
        periodo_id=periodo.id,
        accion=ACCION_REABRIR,
        estado_anterior=True,
        estado_nuevo=False,
        actor=actor,
        motivo=motivo_limpio,
    )

    periodo.cerrado = False
    session.add(evento)
    return evento
