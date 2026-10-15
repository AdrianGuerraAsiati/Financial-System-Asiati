"""El gate de aceptación nunca considera una regresión omitida como PASS."""
from types import SimpleNamespace

import pytest

from ops import validar_regresion_privada_wallets as gate


def test_runner_rechaza_omisiones_aunque_pytest_devuelva_ok(monkeypatch, capsys):
    def pytest_simulado(args, plugins):
        assert args[0:2] == ["-q", "-ra"]
        assert tuple(args[2:]) == gate.PRUEBAS_PRIVADAS
        plugins[0].pytest_runtest_logreport(SimpleNamespace(skipped=True))
        return pytest.ExitCode.OK

    monkeypatch.setattr(gate.pytest, "main", pytest_simulado)
    assert gate.ejecutar() == 2
    assert "pruebas omitidas" in capsys.readouterr().err


def test_runner_retorna_ok_sin_omisiones(monkeypatch):
    def pytest_simulado(args, plugins):
        plugins[0].pytest_runtest_logreport(SimpleNamespace(skipped=False))
        return pytest.ExitCode.OK

    monkeypatch.setattr(gate.pytest, "main", pytest_simulado)
    assert gate.ejecutar() == 0


def test_runner_propagara_fallo_de_regresion(monkeypatch):
    monkeypatch.setattr(
        gate.pytest,
        "main",
        lambda args, plugins: pytest.ExitCode.TESTS_FAILED,
    )
    assert gate.ejecutar() == int(pytest.ExitCode.TESTS_FAILED)
