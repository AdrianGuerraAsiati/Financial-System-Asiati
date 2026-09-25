from datetime import date

import pytest

from app.core.periodos import Periodo
from app.core.periodos.errors import PeriodoCerradoError
from app.core.periodos.service import actualizar_rango


def test_open_period_can_change_date_range() -> None:
    periodo = Periodo(
        empresa_id=1,
        fecha_inicio=date(2026, 9, 1),
        fecha_fin=date(2026, 9, 30),
    )

    actualizar_rango(
        periodo,
        fecha_inicio=date(2026, 9, 2),
        fecha_fin=date(2026, 9, 29),
    )

    assert periodo.fecha_inicio == date(2026, 9, 2)
    assert periodo.fecha_fin == date(2026, 9, 29)


def test_closed_period_rejects_date_range_changes() -> None:
    periodo = Periodo(
        empresa_id=1,
        fecha_inicio=date(2026, 9, 1),
        fecha_fin=date(2026, 9, 30),
        cerrado=True,
    )

    with pytest.raises(PeriodoCerradoError):
        actualizar_rango(
            periodo,
            fecha_inicio=date(2026, 9, 2),
            fecha_fin=date(2026, 9, 29),
        )

    assert periodo.fecha_inicio == date(2026, 9, 1)
    assert periodo.fecha_fin == date(2026, 9, 30)
