import app.dashboard.api as dashboard_api
from app.core.usuarios.roles import (
    ROL_ANALISTA_TESORERIA,
    ROL_CONCILIACION,
    ROL_SUPER_ADMINISTRADOR,
)
from app.motores.compras_supply_chain.demo import construir_fuente_demo
from tests.apoyo_auth import (
    cliente_con_rol,
    crear_empresa,
    crear_hallazgo,
    crear_periodo,
)


def test_principal_dashboard_composes_visible_modules_without_new_scores(
    monkeypatch,
) -> None:
    empresa_id = crear_empresa("Dashboard principal")
    periodo_id = crear_periodo(empresa_id)
    crear_hallazgo(periodo_id)
    fuente = construir_fuente_demo(empresa_id=empresa_id)
    monkeypatch.setattr(
        dashboard_api,
        "obtener_fuente_compras",
        lambda: fuente,
    )

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

    compras = next(
        item for item in body["modulos"] if item["codigo"] == "compras"
    )
    assert compras["disponible"] is True
    assert compras["resumen"]["costo_compra_usd"] == "33780.50"
    assert compras["resumen"]["valor_comercial_ddp_usd"] == "48870.75"
    assert compras["resumen"]["ocs_poblacion_actual"] >= 1
    assert compras["accion"]["vista"] == "compras"

    conciliacion = next(
        item for item in body["modulos"] if item["codigo"] == "conciliacion"
    )
    assert conciliacion["resumen"]["hallazgos_abiertos"] == 1
    assert conciliacion["resumen"]["hallazgos_criticos_abiertos"] == 1

    assert any(item["modulo"] == "compras" for item in body["atencion"])
    assert any(item["modulo"] == "conciliacion" for item in body["atencion"])


def test_principal_dashboard_hides_unassigned_company_before_module_reads(
    monkeypatch,
) -> None:
    permitida = crear_empresa("Dashboard permitida")
    ajena = crear_empresa("Dashboard ajena")
    llamadas = {"compras": 0}

    def no_debe_leer():
        llamadas["compras"] += 1
        raise AssertionError("No debe leer fuentes de empresa no visible")

    monkeypatch.setattr(dashboard_api, "obtener_fuente_compras", no_debe_leer)

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
