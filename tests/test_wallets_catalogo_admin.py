"""Pruebas unitarias de límites del catálogo de cobertura."""
from unittest.mock import Mock, patch

import pytest

from app.motores.conciliacion_wallets.catalogo_admin import (
    CatalogoCongeladoError, agregar, aprobar, quitar, validar_identidad,
)


def test_normaliza_identidad_y_no_admite_wiilog_con_correo():
    assert validar_identidad("pagos", "  TEST@EXAMPLE.TEST  ") == ("pagos", "test@example.test")
    assert validar_identidad("wiilog", None) == ("wiilog", "")
    with pytest.raises(ValueError):
        validar_identidad("wiilog", "no-se-versiona@example.test")


def test_no_permite_editar_catalogo_ya_aprobado():
    session = Mock()
    with patch("app.motores.conciliacion_wallets.catalogo_admin.periodo_bloqueado"), patch(
        "app.motores.conciliacion_wallets.catalogo_admin._aprobacion", return_value=Mock()
    ):
        with pytest.raises(CatalogoCongeladoError):
            agregar(session, empresa_id=1, periodo_id=2, usuario_id=3,
                    tipo_wallet="wiilog", identidad_wallet=None)
        with pytest.raises(CatalogoCongeladoError):
            quitar(session, empresa_id=1, periodo_id=2, item_id=5, usuario_id=3, motivo="baja")


def test_aprobador_no_puede_aprobar_sus_propias_wallets():
    session = Mock()
    with patch("app.motores.conciliacion_wallets.catalogo_admin.periodo_bloqueado"), patch(
        "app.motores.conciliacion_wallets.catalogo_admin._aprobacion", return_value=None
    ), patch("app.motores.conciliacion_wallets.catalogo_admin._filas",
             return_value=[Mock(registrado_por=3)]):
        with pytest.raises(ValueError, match="no puede aprobar"):
            aprobar(session, empresa_id=1, periodo_id=2, usuario_id=3, motivo="validado")


def test_no_aprueba_catalogo_vacio():
    session = Mock()
    with patch("app.motores.conciliacion_wallets.catalogo_admin.periodo_bloqueado"), patch(
        "app.motores.conciliacion_wallets.catalogo_admin._aprobacion", return_value=None
    ), patch("app.motores.conciliacion_wallets.catalogo_admin._filas", return_value=[]):
        with pytest.raises(ValueError, match="vacío"):
            aprobar(session, empresa_id=1, periodo_id=2, usuario_id=3, motivo="validado")
