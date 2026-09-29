from fastapi.testclient import TestClient

from app.main import app


def test_cartera_view_exposes_source_discovery_controls() -> None:
    html = TestClient(app).get("/")
    js = TestClient(app).get("/static/app.js")

    assert html.status_code == 200
    assert 'id="cartera-descubrir-fuente"' in html.text
    assert 'id="cartera-descubrimiento-contenido"' in html.text

    assert js.status_code == 200
    assert "/api/v1/cartera/fuente/descubrir" in js.text
    assert "cargarDescubrimientoCartera" in js.text
    assert "rango_sugerido" in js.text
