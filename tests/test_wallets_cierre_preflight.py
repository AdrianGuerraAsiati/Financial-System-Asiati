"""Pruebas del contrato de preflight, sin realizar cierres reales."""
from unittest.mock import Mock

import pytest

from app.motores.conciliacion_wallets.cierre_preflight import diagnostico_cierre_wallets


def test_rechaza_periodo_de_otra_empresa():
    session = Mock()
    session.get.return_value = Mock(empresa_id=99)
    with pytest.raises(ValueError, match="no pertenece"):
        diagnostico_cierre_wallets(session, empresa_id=1, periodo_id=10)
    session.scalars.assert_not_called()


def test_no_autoriza_cierre_sin_reglas_aprobadas():
    session = Mock()
    session.get.return_value = Mock(empresa_id=1, cerrado=False)
    session.scalars.side_effect = [iter([]), iter([])]
    resultado = diagnostico_cierre_wallets(session, empresa_id=1, periodo_id=10)
    assert resultado["puede_cerrar"] is False
    assert resultado["ejecuciones_ultimas"] == 0
    assert resultado["razones"]


def test_ultima_ejecucion_bloqueada_impide_dar_false_pass():
    session = Mock()
    session.get.return_value = Mock(empresa_id=1, cerrado=False)
    ultimo = Mock(id=11, tipo_wallet="pagos", identidad_wallet="a@example.test",
                  bloqueado=True, resultado={"c0": {"cuadra": False}})
    anterior = Mock(id=10, tipo_wallet="pagos", identidad_wallet="a@example.test",
                    bloqueado=False, resultado={"c0": {"cuadra": True}})
    session.scalars.side_effect = [iter([ultimo, anterior]), iter([])]
    resultado = diagnostico_cierre_wallets(session, empresa_id=1, periodo_id=10)
    assert resultado["ejecuciones_ultimas"] == 1
    assert resultado["ejecuciones_bloqueadas"][0]["ejecucion_id"] == 11
    assert resultado["puede_cerrar"] is False
