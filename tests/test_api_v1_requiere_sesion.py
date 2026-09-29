"""Ningún endpoint de /api/v1 responde sin sesión, salvo login y logout."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


PUBLICOS = {("POST", "/api/v1/auth/login"), ("POST", "/api/v1/auth/logout")}


def _endpoints_v1() -> list[tuple[str, str]]:
    return sorted(
        (metodo.upper(), ruta)
        for ruta, operaciones in app.openapi()["paths"].items()
        if ruta.startswith("/api/v1")
        for metodo in operaciones
    )


def test_session_endpoints_are_registered() -> None:
    assert ("GET", "/api/v1/auth/me") in _endpoints_v1()
    assert ("POST", "/api/v1/hallazgos/{hallazgo_id}/escalar") in _endpoints_v1()


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [endpoint for endpoint in _endpoints_v1() if endpoint not in PUBLICOS],
)
def test_endpoint_rejects_requests_without_session(
    metodo: str, ruta: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # El motor de base de datos se crea sin conectarse: sin cookie no hay consulta.
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://nadie:nada@127.0.0.1:1/nada")
    monkeypatch.setenv("JWT_SECRET", "s" * 40)
    client = TestClient(app, base_url="https://testserver")

    respuesta = client.request(metodo, ruta.replace("{usuario_id}", "1").replace("{hallazgo_id}", "1"), json={})

    assert respuesta.status_code == 401
    assert "Inicia sesión" in respuesta.json()["detail"]
