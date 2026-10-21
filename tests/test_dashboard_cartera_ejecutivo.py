"""Indicadores de Cartera en Inicio sin consultar Sheets ni inventar cobros."""
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dashboard.cartera_indicadores import indicadores_cartera
from app.main import app
from app.motores.cartera_ocs.snapshots import (
    FilaSnapshotCartera,
    SnapshotFuenteCartera,
    guardar_snapshot_cartera,
)
from tests.apoyo_auth import cliente_superadmin, crear_empresa, engine


def test_calculo_exacto_proyecciones_mora_y_horizonte_de_treinta_dias():
    filas = [
        ("OPERACIONES", {"oc": "GM1"}),
        ("OPERACIONES", {"oc": "gm1"}),
        ("OPERACIONES", {"oc": "GM2"}),
        ("MORA", {"monto": "1250.25"}),
        ("PROYECCION", {"oc": "GM1", "fecha": "2026-10-29", "monto": "11760.00"}),
        ("PROYECCION", {"oc": "GM1", "fecha": "2026-11-15", "monto": "100.00"}),
        ("PROYECCION", {"oc": "GM2", "fecha": "2026-09-29", "monto": "2000.00"}),
        ("PROYECCION", {"oc": "", "fecha": "2026-10-25", "monto": "0.50"}),
        ("PROYECCION", {"oc": "GM3", "fecha": "2026-10-28", "monto": "-50.00"}),
        ("PROYECCION", {"oc": "GM4", "fecha": "2026-10-29", "monto": "no es importe"}),
    ]
    valores = indicadores_cartera(
        filas, tipos_validos={"OPERACIONES", "MORA", "PROYECCION"},
        hoy=date(2026, 10, 21)
    )
    assert valores["ocs_operaciones"] == 2
    assert valores["ocs_proyectadas"] == 2
    assert valores["proyecciones_con_oc"] == 3
    assert valores["registros_proyeccion_utiles"] == 4
    assert valores["monto_proyectado_usd"] == "13860.50"
    assert valores["monto_mora_usd"] == "1250.25"
    assert valores["proximos_30_dias_usd"] == "11860.50"
    assert valores["fechas_anteriores_usd"] == "2000.00"
    assert [x["mes"] for x in valores["meses_futuros"]] == [
        "2026-10", "2026-11", "2026-12", "2027-01", "2027-02", "2027-03"
    ]
    assert valores["meses_futuros"][0]["monto_usd"] == "11760.50"
    assert valores["meses_futuros"][1]["monto_usd"] == "100.00"
    assert valores["meses_futuros"][2]["monto_usd"] == "0.00"
    assert "cobrado" not in valores and "saldo" not in valores


def test_fuentes_no_validadas_permanecen_ausentes_en_vez_de_cero():
    filas = [
        ("MORA", {"monto": "100000.00"}),
        ("PROYECCION", {"oc": "GM1", "fecha": "2026-10-29", "monto": "100.00"}),
    ]
    valores = indicadores_cartera(
        filas, tipos_validos={"PROYECCION"}, hoy=date(2026, 10, 21)
    )
    assert valores["monto_mora_usd"] is None
    assert valores["monto_proyectado_usd"] == "100.00"
    assert valores["ocs_operaciones"] is None
    sin_validos = indicadores_cartera(
        filas, tipos_validos=set(), hoy=date(2026, 10, 21)
    )
    assert sin_validos["monto_proyectado_usd"] is None
    assert sin_validos["meses_futuros"] == []


def test_dashboard_lee_solo_snapshot_persistido_autorizado():
    permitido = crear_empresa("Resumen Cartera desde DB")
    ajeno = crear_empresa("Resumen empresa separada")
    snapshot = SnapshotFuenteCartera(
        cargado_en=__import__("datetime").datetime(
            2026, 10, 21, 17, 0, tzinfo=__import__("datetime").timezone.utc
        ),
        spreadsheet_id="source_test_cartera",
        rangos={"PROYECCION": "PROYECCIONES!A:Q", "MORA": "MORA!A:E"},
        diagnosticos=(
            {"tipo": "PROYECCION", "valido": True, "filas_datos": 2, "configurado": True},
            {"tipo": "MORA", "valido": True, "filas_datos": 1, "configurado": True},
            {"tipo": "OPERACIONES", "valido": False, "filas_datos": 1, "configurado": True},
        ),
        filas=(
            FilaSnapshotCartera(
                tipo="PROYECCION", fila_fuente=2, crudo={"valores": ["x"]},
                normalizado={"oc": "GM999", "fecha": "2026-11-01", "monto": "500.15"}
            ),
            FilaSnapshotCartera(
                tipo="PROYECCION", fila_fuente=3, crudo={"valores": ["y"]},
                normalizado={"oc": "GM999", "fecha": "2026-11-13", "monto": "1.05"}
            ),
            FilaSnapshotCartera(
                tipo="MORA", fila_fuente=2, crudo={"valores": ["z"]},
                normalizado={"cliente": "Cliente de prueba", "monto": "100.50"}
            ),
            FilaSnapshotCartera(
                tipo="OPERACIONES", fila_fuente=2, crudo={"valores": ["no valido"]},
                normalizado={"oc": "NO_DEBE_CONTAR"}
            ),
        ),
    )
    with Session(engine()) as session:
        guardar_snapshot_cartera(session, empresa_id=permitido, snapshot=snapshot)
        session.commit()

    client = cliente_superadmin()
    response = client.get("/api/v1/dashboard/principal", params={"empresa_id": permitido})
    assert response.status_code == 200, response.text
    cartera = next(x for x in response.json()["modulos"] if x["codigo"] == "cartera")
    assert cartera["estado_resumen"] == "CON_CAPTURA"
    assert cartera["disponible"] is True
    assert cartera["resumen"]["indicadores"]["monto_proyectado_usd"] == "501.20"
    assert cartera["resumen"]["indicadores"]["monto_mora_usd"] == "100.50"
    assert cartera["resumen"]["indicadores"]["ocs_proyectadas"] == 1
    assert cartera["resumen"]["indicadores"]["ocs_operaciones"] is None

    vacio = client.get("/api/v1/dashboard/principal", params={"empresa_id": ajeno})
    assert vacio.status_code == 200
    cartera_ajena = next(x for x in vacio.json()["modulos"] if x["codigo"] == "cartera")
    assert cartera_ajena["estado_resumen"] == "SIN_CAPTURA"
    assert "indicadores" not in cartera_ajena["resumen"]


def test_inicio_ofrece_captura_inicial_y_enlaces_contextuales():
    client = TestClient(app)
    page = client.get("/").text
    js = client.get("/static/app.js").text
    css = client.get("/static/inicio_cartera.css")
    assert css.status_code == 200
    assert 'id="inicio-cartera-vision"' in page
    assert 'href="/static/inicio_cartera.css"' in page
    for mark in (
        "renderInicioCartera(", "Generar resumen de Cartera",
        "data-home-cartera-tab", "window.ASIATI_CARTERA_NAV?.activar(",
        "proximos_30_dias_usd", "monto_mora_usd", "monto_proyectado_usd",
        "monedaInicioExacta(", "centavosInicio(",
        '/api/v1/cartera/snapshots?empresa_id='
    ):
        assert mark in js
    assert "inicio-cartera-kpis" in css.text
