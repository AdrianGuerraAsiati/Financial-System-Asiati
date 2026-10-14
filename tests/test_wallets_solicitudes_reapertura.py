"""Solicitud de reapertura: reglas sin efectos sobre el estado financiero."""
from unittest.mock import Mock, patch
import pytest
from app.motores.conciliacion_wallets.solicitudes_reapertura import solicitar, decidir

def test_no_solicita_periodo_abierto():
    session=Mock()
    session.scalar.return_value=Mock(cerrado=False)
    with pytest.raises(ValueError, match="cerrado"):
        solicitar(session,empresa_id=1,periodo_id=2,revision_id=3,usuario_id=4,motivo="x",evidencia_ref="ref")

def test_no_solicita_sin_gestion_autorizada():
    session=Mock()
    session.scalar.side_effect=[Mock(cerrado=True),Mock(conclusion="SIN_IMPACTO",decision="AUTORIZAR_GESTION")]
    with pytest.raises(ValueError,match="autorización"):
        solicitar(session,empresa_id=1,periodo_id=2,revision_id=3,usuario_id=4,motivo="x",evidencia_ref="ref")

def test_no_decide_dos_veces():
    session=Mock()
    session.scalar.side_effect=[Mock(cerrado=True),Mock(decision="APROBADA")]
    with pytest.raises(ValueError,match="ya decidida"):
        decidir(session,empresa_id=1,periodo_id=2,solicitud_id=5,usuario_id=6,decision="APROBADA",motivo="x")

def test_no_aprueba_periodo_ya_abierto():
    session=Mock()
    session.scalar.side_effect=[Mock(cerrado=False),Mock(decision=None,solicitado_por=4)]
    with pytest.raises(ValueError,match="ya está abierto"):
        decidir(session,empresa_id=1,periodo_id=2,solicitud_id=5,usuario_id=6,decision="APROBADA",motivo="x")
