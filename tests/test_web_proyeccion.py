from fastapi.testclient import TestClient

from app.main import app


def test_shell_exposes_payment_projection_view() -> None:
    html = TestClient(app).get("/")
    js = TestClient(app).get("/static/app.js")

    assert html.status_code == 200
    assert 'id="cartera-proyeccion"' in html.text
    assert js.status_code == 200
    assert "/api/v1/cartera/proyeccion" in js.text
