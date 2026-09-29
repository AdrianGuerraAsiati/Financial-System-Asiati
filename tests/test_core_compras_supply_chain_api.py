from app.core.usuarios.roles import (
    ROL_CONCILIACION,
    ROL_SUPER_ADMINISTRADOR,
)
from app.main import app
from app.motores.compras_supply_chain.api import obtener_fuente_compras
from app.motores.compras_supply_chain.dominio import LineaCompra
from tests.apoyo_auth import cliente_con_rol, crear_empresa


def _linea(
    *,
    pais: str = "CO",
    estado: str = "ENVIADO A DESTINO",
    etapa: str = "TRANSITO",
    oc: str = "OC-100",
) -> LineaCompra:
    return LineaCompra(
        pais=pais,
        hoja_fuente=f"INFORME CLIENTES ({pais})",
        fila_fuente=4,
        numero_oc=oc,
        oc_identificada=True,
        cliente="Cliente prueba",
        sku="SKU-1",
        descripcion="Producto",
        proveedor="Proveedor",
        estado_origen=estado,
        estado_normalizado=estado,
        etapa_logistica=etapa,
        situacion_operativa="NORMAL",
        modo_transporte_origen="MARITIMO",
        modo_transporte_normalizado="MARITIMO",
        documento_transporte="BL-1",
        etd="2026-09-01",
        eta="2026-10-01",
        fecha_entrega_bodega_destino="",
        valor_total_compra_usd_origen="1000",
        valor_oci_ddp_origen="1300",
    )


class FuenteFake:
    def __init__(self, empresa_id: int) -> None:
        self.empresa_id = empresa_id
        self.llamadas = 0

    def listar(self, *, empresa_id: int):
        self.llamadas += 1
        assert empresa_id == self.empresa_id
        return (
            _linea(),
            _linea(
                pais="EC",
                estado="EN OTM",
                etapa="POR_DEFINIR",
                oc="OC-200",
            ),
        )


def test_compras_api_lists_lines_and_catalogs_with_authenticated_access() -> None:
    empresa_id = crear_empresa("Compras API")
    fuente = FuenteFake(empresa_id)
    app.dependency_overrides[obtener_fuente_compras] = lambda: fuente
    client, _ = cliente_con_rol(ROL_SUPER_ADMINISTRADOR)

    try:
        response = client.get(
            "/api/v1/compras/lineas",
            params={"empresa_id": empresa_id, "pais": "CO"},
        )
        catalogos = client.get(
            "/api/v1/compras/catalogos",
            params={"empresa_id": empresa_id},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["numero_oc"] == "OC-100"
    assert body["items"][0]["etapa_logistica"] == "TRANSITO"

    assert catalogos.status_code == 200
    catalogos_body = catalogos.json()
    assert catalogos_body["lineas"] == 2
    assert catalogos_body["estados_por_definir"] == {"EN OTM": 1}


def test_compras_api_hides_unassigned_company_before_reading_source() -> None:
    empresa_permitida = crear_empresa("Compras permitida")
    empresa_ajena = crear_empresa("Compras ajena")
    fuente = FuenteFake(empresa_ajena)
    app.dependency_overrides[obtener_fuente_compras] = lambda: fuente
    client, _ = cliente_con_rol(
        ROL_CONCILIACION,
        empresas=(empresa_permitida,),
    )

    try:
        response = client.get(
            "/api/v1/compras/catalogos",
            params={"empresa_id": empresa_ajena},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert fuente.llamadas == 0



def test_compras_api_exposes_safe_oc_grouping_and_quality() -> None:
    empresa_id = crear_empresa("Compras observabilidad")
    fuente = FuenteFake(empresa_id)
    app.dependency_overrides[obtener_fuente_compras] = lambda: fuente
    client, _ = cliente_con_rol(ROL_SUPER_ADMINISTRADOR)

    try:
        ocs = client.get(
            "/api/v1/compras/ocs",
            params={"empresa_id": empresa_id},
        )
        calidad = client.get(
            "/api/v1/compras/calidad",
            params={"empresa_id": empresa_id},
        )
        resumen = client.get(
            "/api/v1/compras/resumen",
            params={"empresa_id": empresa_id},
        )
    finally:
        app.dependency_overrides.clear()

    assert ocs.status_code == 200
    assert ocs.json()["total"] == 2
    assert {item["numero_oc"] for item in ocs.json()["items"]} == {
        "OC-100",
        "OC-200",
    }

    assert resumen.status_code == 200
    assert resumen.json()["ocs_identificadas"] == 2
    assert resumen.json()["ocs_mixtas"] == 0
    assert resumen.json()["lineas_estado_por_definir"] == 1

    assert calidad.status_code == 200
    body = calidad.json()
    assert body["lineas_evaluadas"] == 2
    codigos = {item["codigo"] for item in body["observaciones"]}
    assert "ESTADO_POR_DEFINIR" in codigos
    assert "modifican la fuente" in body["nota"]


def test_source_diagnostics_stay_available_when_schema_is_degraded() -> None:
    from app.motores.compras_supply_chain.google_sheets import (
        ConfiguracionComprasGoogleSheets,
        FuenteComprasGoogleSheets,
    )

    empresa_id = crear_empresa("Compras diagnóstico")

    class ClienteConDrift:
        def obtener_valores(self, *, spreadsheet_id: str, rango: str):
            return [
                ["NUMERO OC", "CLIENTE", "ESTADO", "MODO TRANSPORTE"],
                ["OC-1", "Cliente", "ENTREGADO", "MARITIMO"],
            ]

    fuente = FuenteComprasGoogleSheets(
        cliente=ClienteConDrift(),
        configuracion=ConfiguracionComprasGoogleSheets(
            empresa_id=empresa_id,
            spreadsheet_id="sheet-id",
            rangos_por_pais={"CO": "CO!A:Z", "EC": "EC!A:Z", "CL": "CL!A:Z"},
        ),
    )
    app.dependency_overrides[obtener_fuente_compras] = lambda: fuente
    client, _ = cliente_con_rol(ROL_SUPER_ADMINISTRADOR)

    try:
        diagnostico = client.get(
            "/api/v1/compras/fuente/estado",
            params={"empresa_id": empresa_id},
        )
        lineas = client.get(
            "/api/v1/compras/lineas",
            params={"empresa_id": empresa_id},
        )
    finally:
        app.dependency_overrides.clear()

    assert diagnostico.status_code == 200
    assert diagnostico.json()["estado"] == "DEGRADADO"
    assert diagnostico.json()["solo_lectura"] is True
    assert all(
        "proveedor" in hoja["campos_criticos_faltantes"]
        for hoja in diagnostico.json()["hojas"]
    )

    assert lineas.status_code == 503
    assert "evitar resultados silenciosamente incorrectos" in lineas.json()["detail"]
