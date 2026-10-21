from fastapi.testclient import TestClient

from app.main import app


def test_cartera_operations_has_search_and_pagination_controls() -> None:
    client = TestClient(app)
    html = client.get("/")
    js = client.get("/static/app.js")
    css = client.get("/static/styles.css")

    assert html.status_code == 200
    assert js.status_code == 200
    assert css.status_code == 200

    for control in (
        "cartera-operaciones-buscar",
        "cartera-operaciones-por-pagina",
        "cartera-operaciones-total",
        "cartera-operaciones-anterior",
        "cartera-operaciones-pagina",
        "cartera-operaciones-siguiente",
    ):
        assert f'id="{control}"' in html.text

    assert "CARTERA_OPERACIONES_PAGE_SIZE = 20" in js.text
    assert "renderizarOperacionesCartera" in js.text
    assert "carteraOperacionesFiltradas.slice(" in js.text
    assert "carteraOperacionesBody" not in js.text
    assert ".cartera-table" in css.text


def test_cartera_source_diagnostics_are_collapsible() -> None:
    js = TestClient(app).get("/static/app.js")

    assert js.status_code == 200
    assert 'class="cartera-source-diagnostics"' in js.text
    assert "diagnosticos.some((item) => !item.valido)" in js.text
