from fastapi.testclient import TestClient

from app.main import app


def test_root_serves_block1_application_shell() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "Plataforma Financiera ASIATI" in response.text
    assert "Cartera" in response.text
    assert "Wallets" in response.text
    assert "Chin Chin" in response.text
    assert 'id="operaciones"' in response.text
    assert 'id="detalle-operacion"' in response.text
    assert 'id="comprobantes-pendientes"' in response.text
    assert 'id="form-comprobante"' in response.text


def test_shell_javascript_consumes_existing_cartera_endpoints() -> None:
    response = TestClient(app).get("/static/app.js")

    assert response.status_code == 200
    assert "/cartera/operaciones" in response.text
    assert "/cartera/comprobantes/pendientes" in response.text
    assert "/cartera/comprobantes" in response.text
    assert "/archivo?empresa_id=" in response.text
