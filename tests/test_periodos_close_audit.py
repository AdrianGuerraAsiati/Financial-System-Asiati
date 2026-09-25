from datetime import date

import pytest

from app.core.periodos import Periodo
from app.core.periodos.errors import MotivoReaperturaRequeridoError
from app.core.periodos.history import ACCION_CERRAR, ACCION_REABRIR
from app.core.periodos.service import cerrar_periodo, reabrir_periodo


class SpySession:
    def __init__(self) -> None:
        self.added = []

    def add(self, entity) -> None:
        self.added.append(entity)


def _periodo(*, cerrado: bool = False) -> Periodo:
    return Periodo(
        id=10,
        empresa_id=1,
        fecha_inicio=date(2026, 9, 1),
        fecha_fin=date(2026, 9, 30),
        cerrado=cerrado,
    )


def test_period_model_does_not_expose_direct_close_mutator() -> None:
    assert not hasattr(Periodo, "cerrar")


def test_close_records_traceable_event() -> None:
    session = SpySession()
    periodo = _periodo()

    evento = cerrar_periodo(
        session,
        periodo,
        actor="sistemas@asiati.com.co",
        motivo="Cierre mensual validado",
        verificar_criticos=lambda _session, _periodo_id: False,
    )

    assert periodo.cerrado is True
    assert evento in session.added
    assert evento.periodo_id == 10
    assert evento.accion == ACCION_CERRAR
    assert evento.estado_anterior is False
    assert evento.estado_nuevo is True
    assert evento.actor == "sistemas@asiati.com.co"
    assert evento.motivo == "Cierre mensual validado"


def test_reopen_requires_reason_and_records_event() -> None:
    session = SpySession()
    periodo = _periodo(cerrado=True)

    with pytest.raises(MotivoReaperturaRequeridoError):
        reabrir_periodo(
            session,
            periodo,
            actor="sistemas@asiati.com.co",
            motivo="   ",
        )

    assert periodo.cerrado is True
    assert session.added == []

    evento = reabrir_periodo(
        session,
        periodo,
        actor="sistemas@asiati.com.co",
        motivo="Corrección aprobada del cierre",
    )

    assert periodo.cerrado is False
    assert evento.accion == ACCION_REABRIR
    assert evento.estado_anterior is True
    assert evento.estado_nuevo is False
