"""Pruebas unitarias de límites del catálogo de cobertura."""
from unittest.mock import Mock, patch
from datetime import date

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


def test_no_permite_wallet_ajena_o_no_parametrizada():
    session = Mock()
    with patch("app.motores.conciliacion_wallets.catalogo_admin.periodo_bloqueado"), patch(
        "app.motores.conciliacion_wallets.catalogo_admin._aprobacion", return_value=None
    ), patch(
        "app.motores.conciliacion_wallets.catalogo_admin.catalogo_de_empresa",
        return_value={"wiilog": False, "tiendas": [], "pagos": []},
    ):
        with pytest.raises(ValueError, match="no está parametrizada"):
            agregar(session, empresa_id=1, periodo_id=2, usuario_id=3,
                    tipo_wallet="pagos", identidad_wallet="otra@example.test")
    session.add.assert_not_called()


def test_alta_acepta_wallet_parametrizada_y_deja_auditoria():
    session = Mock()
    session.scalar.return_value = None
    with patch("app.motores.conciliacion_wallets.catalogo_admin.periodo_bloqueado"), patch(
        "app.motores.conciliacion_wallets.catalogo_admin._aprobacion", return_value=None
    ), patch(
        "app.motores.conciliacion_wallets.catalogo_admin.catalogo_de_empresa",
        return_value={"wiilog": False, "tiendas": [], "pagos": [{"usuario_email": "wallet@example.test"}]},
    ), patch("app.motores.conciliacion_wallets.catalogo_admin.registrar_auditoria") as auditar:
        item = agregar(session, empresa_id=1, periodo_id=2, usuario_id=3,
                       tipo_wallet="pagos", identidad_wallet="WALLET@example.test")
    assert item.identidad_wallet == "wallet@example.test"
    session.add.assert_called_once()
    auditar.assert_called_once()


def test_no_aprueba_vigencia_sin_fechas():
    session = Mock()
    periodo = Mock(fecha_inicio=date(2026, 9, 1), fecha_fin=date(2026, 9, 30))
    fila = Mock(registrado_por=3, vigente_desde=None, vigente_hasta=None)
    with patch("app.motores.conciliacion_wallets.catalogo_admin.periodo_bloqueado", return_value=periodo), patch(
        "app.motores.conciliacion_wallets.catalogo_admin._aprobacion", return_value=None
    ), patch("app.motores.conciliacion_wallets.catalogo_admin._filas", return_value=[fila]):
        with pytest.raises(ValueError, match="acreditar vigencia"):
            aprobar(session, empresa_id=1, periodo_id=2, usuario_id=4, motivo="verificado")


def test_no_aprueba_vigencia_parcial():
    session = Mock()
    periodo = Mock(fecha_inicio=date(2026, 9, 1), fecha_fin=date(2026, 9, 30))
    fila = Mock(registrado_por=3, vigente_desde=date(2026, 9, 10),
                vigente_hasta=date(2026, 9, 30))
    with patch("app.motores.conciliacion_wallets.catalogo_admin.periodo_bloqueado", return_value=periodo), patch(
        "app.motores.conciliacion_wallets.catalogo_admin._aprobacion", return_value=None
    ), patch("app.motores.conciliacion_wallets.catalogo_admin._filas", return_value=[fila]):
        with pytest.raises(ValueError, match="acreditar vigencia"):
            aprobar(session, empresa_id=1, periodo_id=2, usuario_id=4, motivo="verificado")


def test_rechaza_fechas_invertidas_en_alta():
    with pytest.raises(ValueError, match="fecha inicial"):
        agregar(Mock(), empresa_id=1, periodo_id=2, usuario_id=3,
                tipo_wallet="pagos", identidad_wallet="a@example.test",
                vigente_desde=date(2026, 9, 30), vigente_hasta=date(2026, 9, 1))
