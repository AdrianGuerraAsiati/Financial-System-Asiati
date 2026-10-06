import pytest

from app.motores.conciliacion_wallets.wiilog.integracion import (
    ConfiguracionWiilogFaltanteError,
    cargar_parametros_wiilog,
)


def _regla_traslado(parametros: dict) -> dict:
    return next(
        regla
        for regla in parametros["conceptos_wallet"]
        if regla["codigo"] == "TRASLADO_WALLET_WIILOG"
    )


def test_wiilog_runtime_identifier_resolves_placeholder() -> None:
    parametros = cargar_parametros_wiilog(
        wallet_principal_email="wallet-principal@wiilog.test",
    )

    regla = _regla_traslado(parametros)
    assert "{{WIILOG_WALLET_PRINCIPAL_EMAIL}}" not in regla["empieza_con"]
    assert "WALLET-PRINCIPAL@WIILOG.TEST" in regla["empieza_con"].upper()


def test_wiilog_runtime_identifier_is_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WIILOG_WALLET_PRINCIPAL_EMAIL", raising=False)

    with pytest.raises(RuntimeError, match="WIILOG_WALLET_PRINCIPAL_EMAIL"):
        cargar_parametros_wiilog()


def test_missing_runtime_identifier_has_operator_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WIILOG_WALLET_PRINCIPAL_EMAIL", "   ")

    with pytest.raises(ConfiguracionWiilogFaltanteError) as error:
        cargar_parametros_wiilog()

    assert "Falta configurar la wallet principal de Wiilog" in str(error.value)
