from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.motores.compras_supply_chain.api import obtener_fuente_compras
from app.motores.compras_supply_chain.contrato import analizar_encabezados
from app.motores.compras_supply_chain.dominio import LineaCompra
from app.motores.compras_supply_chain.google_sheets import (
    FilaCrudaCompra,
    SnapshotCompras,
)
from app.motores.compras_supply_chain.model import CompraSnapshotLinea
from app.motores.compras_supply_chain.persistencia import guardar_snapshot
from tests.apoyo_auth import (
    cliente_con_rol,
    crear_empresa,
    engine,
)
from app.core.usuarios.roles import ROL_SUPER_ADMINISTRADOR


def _linea(pais: str, fila: int) -> LineaCompra:
    return LineaCompra(
        pais=pais,
        hoja_fuente=f"INFORME CLIENTES ({pais})",
        fila_fuente=fila,
        numero_oc=f"OC-{pais}-1",
        oc_identificada=True,
        cliente="Cliente prueba",
        sku="SKU-1",
        descripcion="Producto",
        proveedor="Proveedor",
        estado_origen="EN PRODUCCION",
        estado_normalizado="EN PRODUCCION",
        etapa_logistica="PRODUCCION",
        situacion_operativa="NORMAL",
        modo_transporte_origen="MARITIMO",
        modo_transporte_normalizado="MARITIMO",
        documento_transporte="",
        etd="",
        eta="",
        fecha_entrega_bodega_destino="",
        valor_total_compra_usd_origen="100.00",
        valor_oci_ddp_origen="130.00",
    )


def _snapshot() -> SnapshotCompras:
    headers = [
        "NUMERO OC",
        "CLIENTE",
        "PROVEEDOR",
        "ESTADO",
        "MODO TRANSPORTE",
        "VALOR TOTAL COMPRA USD",
        "VALOR OCI (DDP)",
    ]
    lineas = tuple(_linea(pais, 2) for pais in ("CO", "EC", "CL"))
    diagnosticos = tuple(
        analizar_encabezados(
            headers,
            pais=pais,
            rango=f"'{linea.hoja_fuente}'!A:G",
            filas_datos=1,
        )
        for pais, linea in zip(("CO", "EC", "CL"), lineas, strict=True)
    )
    filas_crudas = tuple(
        FilaCrudaCompra(
            pais=pais,
            hoja_fuente=linea.hoja_fuente,
            fila_fuente=2,
            valores=(
                f"OC-{pais}-1",
                "Cliente prueba",
                "Proveedor",
                "EN PRODUCCION",
                "MARITIMO",
                "100.00",
                "130.00",
            ),
        )
        for pais, linea in zip(("CO", "EC", "CL"), lineas, strict=True)
    )
    return SnapshotCompras(
        cargado_en=datetime(2026, 9, 29, 18, 0, tzinfo=timezone.utc),
        lineas=lineas,
        diagnosticos=diagnosticos,
        filas_crudas=filas_crudas,
    )


def test_guardar_snapshot_is_append_only_and_idempotent_by_content_hash() -> None:
    empresa_id = crear_empresa("Compras snapshots")
    snapshot = _snapshot()

    with Session(engine()) as session:
        primero, creado_primero = guardar_snapshot(
            session,
            empresa_id=empresa_id,
            spreadsheet_id="sheet-123",
            modo_fuente="GOOGLE_SHEETS",
            rangos_por_pais={
                "CO": "'INFORME CLIENTES (CO)'!A:G",
                "EC": "'INFORME CLIENTES (EC)'!A:G",
                "CL": "'INFORME CLIENTES (CL)'!A:G",
            },
            snapshot=snapshot,
        )
        session.commit()
        primero_id = primero.id

    with Session(engine()) as session:
        segundo, creado_segundo = guardar_snapshot(
            session,
            empresa_id=empresa_id,
            spreadsheet_id="sheet-123",
            modo_fuente="GOOGLE_SHEETS",
            rangos_por_pais={
                "CO": "'INFORME CLIENTES (CO)'!A:G",
                "EC": "'INFORME CLIENTES (EC)'!A:G",
                "CL": "'INFORME CLIENTES (CL)'!A:G",
            },
            snapshot=snapshot,
        )
        session.commit()

        assert segundo.id == primero_id
        assert creado_primero is True
        assert creado_segundo is False

        filas = tuple(
            session.scalars(
                select(CompraSnapshotLinea)
                .where(CompraSnapshotLinea.snapshot_id == primero_id)
                .order_by(CompraSnapshotLinea.pais)
            )
        )
        assert len(filas) == 3
        assert filas[0].crudo["valores"][0] == "OC-CL-1"
        assert filas[0].normalizado["numero_oc"] == "OC-CL-1"


class FuenteSnapshotFake:
    def __init__(self, empresa_id: int) -> None:
        self.empresa_id = empresa_id
        self.configuracion = type(
            "Config",
            (),
            {
                "spreadsheet_id": "sheet-api",
                "modo_fuente": "GOOGLE_SHEETS",
                "rangos_por_pais": {
                    "CO": "CO!A:G",
                    "EC": "EC!A:G",
                    "CL": "CL!A:G",
                },
            },
        )()

    def obtener_snapshot(self, *, empresa_id: int, forzar_lectura: bool = False):
        assert empresa_id == self.empresa_id
        assert forzar_lectura is True
        return _snapshot()


def test_api_can_capture_and_list_auditable_snapshots() -> None:
    empresa_id = crear_empresa("Compras snapshot API")
    fuente = FuenteSnapshotFake(empresa_id)
    app.dependency_overrides[obtener_fuente_compras] = lambda: fuente
    client, _ = cliente_con_rol(ROL_SUPER_ADMINISTRADOR)

    try:
        creada = client.post(
            "/api/v1/compras/snapshots",
            params={"empresa_id": empresa_id},
        )
        listado = client.get(
            "/api/v1/compras/snapshots",
            params={"empresa_id": empresa_id},
        )
    finally:
        app.dependency_overrides.clear()

    assert creada.status_code == 201
    body = creada.json()
    assert body["creado"] is True
    assert body["snapshot"]["lineas"] == 3
    assert body["snapshot"]["esquema_valido"] is True
    assert len(body["snapshot"]["contenido_hash"]) == 64

    assert listado.status_code == 200
    lista = listado.json()
    assert lista["total"] >= 1
    assert any(
        item["id"] == body["snapshot"]["id"]
        for item in lista["items"]
    )
