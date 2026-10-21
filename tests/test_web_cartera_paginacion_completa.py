"""Contratos UX de búsqueda y paginación completa de Cartera."""
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.main import app
from app.motores.cartera_ocs.snapshots import _filtro_snapshots_cartera
from app.motores.cartera_ocs.snapshot_model import CarteraSnapshot

ROOT = Path(__file__).resolve().parents[1]


def test_shell_conecta_paginadores_antes_de_app_y_mantiene_permisos():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    html = response.text
    assert html.index('src="/static/cartera_paginacion.js"') < html.index(
        'src="/static/app.js"'
    )
    assert 'id="cartera-operaciones-estado"' in html
    assert 'id="cartera-drive-panel" hidden' in html
    assert 'id="comprobantes-pendientes"' in html


def test_listados_tienen_filtrado_paginacion_y_texto_de_accesibilidad():
    js = TestClient(app).get("/static/cartera_paginacion.js")
    assert js.status_code == 200
    for texto in (
        '"search"', '"Filas por página"', '"Anterior"', '"Siguiente"',
        '"Página "', '"aria-live"', '"aria-label"', 'normalizar',
        'consulta', 'remoto', 'contexto',
    ):
        assert texto in js.text
    api = TestClient(app).get("/static/app.js")
    assert api.status_code == 200
    for listado in ("mora", "proyeccion", "pendientes", "snapshots", "calidad", "descubrimiento"):
        assert 'id: "' + listado + '"' in api.text
    assert 'paginadorSnapshots.cargar()' in api.text
    assert 'paginadorSnapshots.primera()' in api.text
    assert "actualizarEstadosOperaciones()" in api.text


def test_drive_pagina_listado_y_filtra_soportes_sin_exponer_otros_permisos():
    drive = TestClient(app).get("/static/cartera_drive.js")
    assert drive.status_code == 200
    for token in (
        "cartera-drive-por-pagina", "cartera-drive-soportes-buscar",
        "cartera-drive-soportes-por-pagina", "renderSoportes()",
        'sesion?.permisos?.["cartera.ver"] === "TODAS"',
    ):
        assert token in drive.text
    inventory = TestClient(app).get("/static/ocs_drive.html")
    assert inventory.status_code == 200
    assert 'id="buscar"' in inventory.text
    assert 'id="tamano"' in inventory.text
    assert "URLSearchParams" in inventory.text


def test_snapshots_busqueda_es_acotada_a_empresa_y_no_crea_registros():
    conditions = _filtro_snapshots_cartera(17, "abc123")
    query = select(CarteraSnapshot.id).where(*conditions)
    sql = str(query.compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    ))
    assert "empresa_id = 17" in sql
    assert "contenido_hash LIKE" in sql
    conditions_by_id = _filtro_snapshots_cartera(17, "123")
    id_query = select(CarteraSnapshot.id).where(*conditions_by_id)
    id_sql = str(id_query.compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    ))
    assert "cartera_snapshots.id = 123" in id_sql
    assert "empresa_id = 17" in id_sql


def test_api_snapshot_tiene_offset_y_busqueda_con_limites():
    from app.motores.cartera_ocs.api import router

    rutas = {route.path: route for route in router.routes if hasattr(route, "path")}
    path = "/cartera/snapshots"
    assert path in rutas
    nombres = set(rutas[path].dependant.query_params[i].name for i in range(len(rutas[path].dependant.query_params)))
    assert {"empresa_id", "limit", "offset", "buscar"}.issubset(nombres)


def test_estilo_compartido_no_rompe_scroll_horizontal_en_tablas():
    css = TestClient(app).get("/static/asiati_v2.css")
    assert css.status_code == 200
    assert ".cartera-list-toolbar" in css.text
    assert ".cartera-list-footer" in css.text
    assert "@media(max-width:620px)" in css.text
