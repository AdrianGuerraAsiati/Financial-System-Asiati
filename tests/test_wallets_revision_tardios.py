"""Controles de revisión segregada de incidencias, sin impacto financiero."""
from unittest.mock import Mock, patch

import pytest

from app.motores.conciliacion_wallets.revision_tardios import revisar, decidir


def test_revision_exige_evidencia_y_motivo():
    with patch("app.motores.conciliacion_wallets.revision_tardios._movimiento", return_value=Mock(id=7)):
        with pytest.raises(ValueError, match="justificación"):
            revisar(Mock(), empresa_id=1, periodo_id=2, movimiento_id=7, usuario_id=4,
                    conclusion="REQUIERE_CORRECCION", justificacion=" ", evidencia_revision="ref")


def test_decision_exige_revision_previa():
    session = Mock()
    session.scalar.return_value = None
    with patch("app.motores.conciliacion_wallets.revision_tardios._movimiento", return_value=Mock(id=7)):
        with pytest.raises(ValueError, match="revisión técnica"):
            decidir(session, empresa_id=1, periodo_id=2, movimiento_id=7, usuario_id=5,
                    decision="AUTORIZAR_GESTION", justificacion="validado")


def test_revisor_no_puede_aprobar_su_revision():
    session = Mock()
    fila = Mock(revisado_por=5, decision=None)
    session.scalar.return_value = fila
    with patch("app.motores.conciliacion_wallets.revision_tardios._movimiento", return_value=Mock(id=7)):
        with pytest.raises(ValueError, match="no puede autorizar"):
            decidir(session, empresa_id=1, periodo_id=2, movimiento_id=7, usuario_id=5,
                    decision="AUTORIZAR_GESTION", justificacion="validado")


def test_no_permite_decidir_dos_veces():
    session = Mock()
    session.scalar.return_value = Mock(revisado_por=4, decision="RECHAZAR_GESTION")
    with patch("app.motores.conciliacion_wallets.revision_tardios._movimiento", return_value=Mock(id=7)):
        with pytest.raises(ValueError, match="Ya existe decisión"):
            decidir(session, empresa_id=1, periodo_id=2, movimiento_id=7, usuario_id=5,
                    decision="AUTORIZAR_GESTION", justificacion="validado")
