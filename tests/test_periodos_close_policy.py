from datetime import date

import pytest

from app.core.periodos import Periodo
from app.core.periodos.errors import HallazgosCriticosAbiertosError
from app.core.periodos.service import cerrar_periodo


class SpySession:
    def __init__(self) -> None:
        self.added = []

    def add(self, entity) -> None:
        self.added.append(entity)


def _periodo() -> Periodo:
    return Periodo(
        id=20,
        empresa_id=1,
        fecha_inicio=date(2026, 9, 1),
        fecha_fin=date(2026, 9, 30),
        cerrado=False,
    )


def test_close_is_rejected_when_hallazgos_reports_open_criticals() -> None:
    session = SpySession()
    periodo = _periodo()

    with pytest.raises(HallazgosCriticosAbiertosError):
        cerrar_periodo(
            session,
            periodo,
            actor="sistemas@asiati.com.co",
            motivo="Intento de cierre",
            verificar_criticos=lambda _session, _periodo_id: True,
        )

    assert periodo.cerrado is False
    assert session.added == []


def test_close_continues_when_hallazgos_reports_no_open_criticals() -> None:
    session = SpySession()
    periodo = _periodo()

    evento = cerrar_periodo(
        session,
        periodo,
        actor="sistemas@asiati.com.co",
        motivo="Cierre validado",
        verificar_criticos=lambda _session, _periodo_id: False,
    )

    assert periodo.cerrado is True
    assert evento in session.added
