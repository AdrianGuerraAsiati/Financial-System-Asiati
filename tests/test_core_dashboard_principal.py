from sqlalchemy.orm import Session

import app.dashboard.api as dashboard_api
from app.core.usuarios.roles import (
    ROL_ANALISTA_TESORERIA,
    ROL_CONCILIACION,
    ROL_SUPER_ADMINISTRADOR,
)
from app.motores.compras_supply_chain.demo import construir_fuente_demo
from app.motores.compras_supply_chain.persistencia import guardar_snapshot
from tests.apoyo_auth import (
    cliente_con_rol,
    crear_empresa,
    crear_hallazgo,
    crear_periodo,
    engine,
)


def _guardar_snapshot_compras_demo(empresa_id: int) -> None:
    fuente = construir_fuente_demo(empresa_id=empresa_id)
    snapshot = fuente.obtener_snapshot(
        empresa_id=empresa_id,
        forzar_lectura=True,
    )
    with Session(engine()) as session:
        guardar_snapshot(
            session,
            empresa_id=empresa_id,
            spreadsheet_id=fuente.configuracion.spreadsheet_id,
            modo_fuente=fuente.configuracion.modo_fuente,
            rangos_por_pais=fuente.configuracion.rangos_por_pais,
            snapshot=snapshot,
        )
        session.commit()


def test_principal_dashboard_composes_visible_modules_without_new_scores() -> None:
    empresa_id = crear_empresa("Dashboard principal")
    periodo_id = crear_periodo(empresa_id)
    crear_hallazgo(periodo_id)
    _guardar_snapshot_compras_demo(empresa_id)

    client, _ = cliente_con_rol(ROL_SUPER_ADMINISTRADOR)
    response = client.get(
        "/api/v1/dashboard/principal",
        params={"empresa_id": empresa_id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["empresa"]["id"] == empresa_id
    assert [item["codigo"] for item in body["modulos"]] == [
        "cartera",
        "compras",
        "conciliacion",
    ]
    assert "scores" not in body
    assert "rankings" not in body
    assert "scores" in body["nota"].lower()
    assert body["versiones"]["compras"] is not None

    compras = next(
        item for item in body["modulos"] if item["codigo"] == "compras"
    )
    assert compras["disponible"] is True
    assert compras["resumen"]["costo_compra_usd"] == "33780.50"
    assert compras["resumen"]["valor_comercial_ddp_usd"] == "48870.75"
    assert compras["resumen"]["ocs_poblacion_actual"] >= 1
    assert compras["accion"]["vista"] == "compras"
    assert compras["snapshot_id"] == body["versiones"]["compras"]

    conciliacion = next(
        item for item in body["modulos"] if item["codigo"] == "conciliacion"
    )
    assert conciliacion["resumen"]["hallazgos_abiertos"] == 1
    assert conciliacion["resumen"]["hallazgos_criticos_abiertos"] == 1
    assert conciliacion["accion"] == {"vista": "wallets", "texto": "Ver wallets"}

    assert any(item["modulo"] == "compras" for item in body["atencion"])
    assert any(item["modulo"] == "conciliacion" for item in body["atencion"])
    conciliacion_atencion = next(
        item for item in body["atencion"] if item["modulo"] == "conciliacion"
    )
    assert conciliacion_atencion["url_destino"] == "wallets"


def test_principal_dashboard_hides_unassigned_company_before_module_reads(
    monkeypatch,
) -> None:
    permitida = crear_empresa("Dashboard permitida")
    ajena = crear_empresa("Dashboard ajena")
    llamadas = {"compras": 0}

    def no_debe_leer(*, empresa_id: int, session: Session):
        llamadas["compras"] += 1
        raise AssertionError("No debe leer módulos de empresa no visible")

    monkeypatch.setattr(dashboard_api, "_leer_compras", no_debe_leer)

    client, _ = cliente_con_rol(
        ROL_CONCILIACION,
        empresas=(permitida,),
    )
    response = client.get(
        "/api/v1/dashboard/principal",
        params={"empresa_id": ajena},
    )

    assert response.status_code == 404
    assert llamadas["compras"] == 0


def test_principal_dashboard_only_returns_modules_allowed_by_role() -> None:
    empresa_id = crear_empresa("Dashboard sin módulos")
    client, _ = cliente_con_rol(
        ROL_ANALISTA_TESORERIA,
        empresas=(empresa_id,),
    )

    response = client.get(
        "/api/v1/dashboard/principal",
        params={"empresa_id": empresa_id},
    )

    assert response.status_code == 200
    assert response.json()["modulos"] == []
    assert response.json()["atencion"] == []
