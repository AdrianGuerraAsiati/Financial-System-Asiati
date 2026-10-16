"""Pruebas sin red de los checks HTTPS de desarrollo."""
import io

import pytest

from ops import verificar_desarrollo_wallets as verificador


class Respuesta:
    status = 200

    def __init__(self, datos):
        self._datos = datos

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _maximo):
        return self._datos


def test_endpoints_satisfactorios(monkeypatch):
    def obtener(url, **_kwargs):
        return Respuesta(b'{"status":"ok"}' if url.endswith("/health") else b'{"status":"ready"}')

    monkeypatch.setattr(verificador, "urlopen", obtener)
    assert verificador.comprobar("https://ejemplo.test") == [
        "PASS: HTTPS /health", "PASS: HTTPS /ready",
    ]


@pytest.mark.parametrize("url", [
    "http://ejemplo.test",
    "https://usuario:pass@ejemplo.test",
    "https://ejemplo.test?token=privado",
    "https://ejemplo.test/health",
])
def test_no_acepta_credenciales_ni_http(url):
    with pytest.raises(ValueError):
        verificador.comprobar(url)


def test_no_acepta_respuesta_no_saludable(monkeypatch):
    monkeypatch.setattr(verificador, "urlopen", lambda url, **kwargs: Respuesta(b'{"status":"bad"}'))
    with pytest.raises(RuntimeError):
        verificador.comprobar("https://ejemplo.test")
