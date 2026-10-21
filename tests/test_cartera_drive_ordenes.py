"""Composición estática de la vista documental, sin requerir PostgreSQL."""
from fastapi.testclient import TestClient
from app.main import app

def test_vista_cartera_incluye_panel_documental_independiente_de_sheets():
    c = TestClient(app)
    pagina = c.get("/")
    modulo = c.get("/static/cartera_drive.js")
    appjs = c.get("/static/app.js")

    assert pagina.status_code == modulo.status_code == appjs.status_code == 200
    assert 'id="cartera-drive-panel"' in pagina.text
    assert 'id="cartera-drive-soportes"' in pagina.text
    assert 'src="/static/cartera_drive.js"' in pagina.text
    assert "/api/v1/cartera/ocs/drive/ordenes" in modulo.text
    assert 'sesion?.permisos?.["cartera.ver"] === "TODAS"' in modulo.text
    assert "textContent" in modulo.text
    assert "innerHTML" not in modulo.text
    assert "window.cargarCarteraDrive()" in appjs.text
    assert "if (!estadoFuente)" in appjs.text
