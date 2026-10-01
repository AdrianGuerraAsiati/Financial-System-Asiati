from fastapi.testclient import TestClient

from app.main import app


def test_shell_exposes_principal_home_dashboard() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert 'id="nav-inicio"' in response.text
    assert 'id="vista-inicio"' in response.text
    assert 'id="inicio-modulos"' in response.text
    assert 'id="inicio-atencion"' in response.text
    assert 'id="inicio-estado-datos"' in response.text
    assert "Requiere atención" in response.text
    assert "No genera scores, rankings" in response.text


def test_shell_wires_principal_dashboard_endpoint_and_navigation() -> None:
    response = TestClient(app).get("/static/app.js")

    assert response.status_code == 200
    assert "/api/v1/dashboard/principal" in response.text
    assert "/api/v1/dashboard/version" in response.text
    assert "Cambios detectados · esperando que termine la edición" in response.text
    assert "cargarDashboardPrincipal({preservar: true})" in response.text
    assert 'mostrarModulo("inicio")' in response.text
    assert 'data-home-view' in response.text
    assert 'sesion.permisos?.["cartera.ver"]' in response.text
    assert 'sesion.permisos?.["compras.ver"]' in response.text
    assert 'sesion.permisos?.["conciliacion.ver"]' in response.text
    assert 'mostrarModulo("wallets")' in response.text
