from fastapi.testclient import TestClient

from app.main import app


def test_cartera_view_exposes_source_status_panel() -> None:
    html = TestClient(app).get("/")
    js = TestClient(app).get("/static/app.js")

    assert html.status_code == 200
    assert 'id="cartera-fuente"' in html.text
    assert 'id="cartera-fuente-contenido"' in html.text
    assert 'id="cartera-refrescar-fuente"' in html.text

    assert js.status_code == 200
    assert "/api/v1/cartera/fuente/estado" in js.text
    assert "cargarCarteraTodo" in js.text
    assert "formatearDecimal" in js.text
    assert "Number(row.valor || 0)" not in js.text
    assert "Number(row.monto || 0)" not in js.text
    assert "Number(item.monto_esperado || 0)" not in js.text
