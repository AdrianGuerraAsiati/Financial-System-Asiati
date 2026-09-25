from collections.abc import Callable
from datetime import date

from sqlalchemy.orm import Session

from app.core.hallazgos import existen_criticos_abiertos
from app.core.periodos.errors import (
    HallazgosCriticosAbiertosError,
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


VerificarCriticos = Callable[[Session, int], bool]


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
    verificar_criticos: VerificarCriticos = existen_criticos_abiertos,
) -> PeriodoCierreEvento:
    """Cierra el período si no existen hallazgos críticos abiertos."""
    if periodo.cerrado:
        raise PeriodoCerradoError("El período ya está cerrado.")

    if verificar_criticos(session, periodo.id):
        raise HallazgosCriticosAbiertosError(
            "El período tiene hallazgos críticos abiertos."
        )

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
