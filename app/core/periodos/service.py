from datetime import date

from app.core.periodos.errors import PeriodoCerradoError
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
