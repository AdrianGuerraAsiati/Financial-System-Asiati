from fastapi.testclient import TestClient

from app.main import app


def test_shell_has_parameters_view_for_category_lists() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert 'id="nav-parametros"' in response.text
    assert 'id="vista-parametros"' in response.text
    assert 'id="parametros-dimension"' in response.text
    assert 'id="parametros-form"' in response.text
    assert "/static/parametros.js" in response.text


def test_parameters_javascript_manages_lists_without_deleting() -> None:
    response = TestClient(app).get("/static/parametros.js")

    assert response.status_code == 200
    assert "/api/v1/dimensiones" in response.text
    assert "dimensiones.gestionar" in response.text
    assert '"PATCH"' in response.text
    assert "Desactivar" in response.text and "Activar" in response.text
    assert '"DELETE"' not in response.text


def test_app_shows_parameters_only_with_permission() -> None:
    response = TestClient(app).get("/static/app.js")

    assert 'permisos?.["dimensiones.gestionar"]' in response.text
    assert "cargarParametrosTodo" in response.text
