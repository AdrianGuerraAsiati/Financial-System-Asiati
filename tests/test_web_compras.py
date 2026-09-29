from fastapi.testclient import TestClient

from app.main import app


def test_shell_exposes_compras_explorer() -> None:
    html = TestClient(app).get("/")
    js = TestClient(app).get("/static/app.js")

    assert html.status_code == 200
    assert 'id="nav-compras"' in html.text
    assert 'id="vista-compras"' in html.text
    assert 'id="compras-kpis-monetarios"' in html.text
    assert 'id="compras-diagnostico"' in html.text
    assert 'id="compras-ocs"' in html.text
    assert 'id="compras-lineas"' in html.text
    assert 'id="compras-calidad"' in html.text
    assert 'id="compras-catalogos"' in html.text

    assert js.status_code == 200
    assert "/api/v1/compras/fuente/estado" in js.text
    assert "/api/v1/compras/ocs" in js.text
    assert "/api/v1/compras/resumen" in js.text
    assert "/api/v1/compras/kpis" in js.text
    assert "/api/v1/compras/lineas" in js.text
    assert "/api/v1/compras/calidad" in js.text
    assert "/api/v1/compras/catalogos" in js.text
    assert 'sesion.permisos?.["compras.ver"]' in js.text


def test_compras_explorer_labels_source_as_read_only() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "Supply Chain · Solo lectura" in response.text
    assert "nunca write-back" in response.text



def test_compras_explorer_exposes_both_monetary_families() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "Costo de compra activo" in response.text
    assert "Valor comercial DDP activo" in response.text
    assert "VALOR TOTAL COMPRA USD" in response.text
    assert "VALOR OCI (DDP)" in response.text
