from fastapi.testclient import TestClient

from app.main import app


def test_cartera_view_exposes_quality_panel() -> None:
    html = TestClient(app).get("/")
    js = TestClient(app).get("/static/app.js")

    assert html.status_code == 200
    assert 'id="cartera-calidad"' in html.text
    assert 'id="cartera-calidad-contenido"' in html.text

    assert js.status_code == 200
    assert "/api/v1/cartera/calidad" in js.text
    assert "cargarCalidadCartera" in js.text
