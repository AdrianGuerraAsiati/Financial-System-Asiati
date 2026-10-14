"""La aplicación documental nunca declara aptitud sin fuente original verificable."""
from unittest.mock import Mock, patch

import pytest

from app.motores.conciliacion_wallets.preflight_aplicacion import evaluar


def test_rechaza_periodo_ajeno():
    session = Mock()
    session.scalar.return_value = None
    with pytest.raises(LookupError, match="Período"):
        evaluar(session, empresa_id=1, periodo_id=2, expediente_id=3)


def test_aprobacion_no_es_aplicacion():
    session = Mock()
    expediente = Mock(id=3, carga_id=4, ejecucion_id=5, movimiento_ref="m1",
                     decision="AUTORIZAR_EJECUCION", decidido_por=9, preparado_por=8,
                     valor_anterior=100, valor_propuesto=110)
    session.scalar.side_effect = [Mock(cerrado=False), expediente, 5, Mock(id=4), 6]
    resultado = evaluar(session, empresa_id=1, periodo_id=2, expediente_id=3)
    assert resultado["puede_aplicar"] is False
    assert resultado["aplicada"] is False
    assert "MOVIMIENTO_E_IMPORTE_ORIGINAL_NO_VERIFICADOS" in resultado["bloqueos"]


def test_sin_autorizacion_bloquea():
    session = Mock()
    expediente = Mock(id=3, carga_id=4, ejecucion_id=5, movimiento_ref="m1",
                     decision=None, decidido_por=None, preparado_por=8,
                     valor_anterior=100, valor_propuesto=110)
    session.scalar.side_effect = [Mock(cerrado=False), expediente, None, None, None]
    resultado = evaluar(session, empresa_id=1, periodo_id=2, expediente_id=3)
    assert "SIN_AUTORIZACION_FINANCIERA" in resultado["bloqueos"]
    assert "SIN_REAPERTURA_VERIFICADA" in resultado["bloqueos"]
