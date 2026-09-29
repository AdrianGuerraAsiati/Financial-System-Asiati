from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.motores.cartera_ocs.api as cartera_api
from app.motores.cartera_ocs.snapshot_model import CarteraSnapshotFila
from app.motores.cartera_ocs.snapshots import (
    FilaSnapshotCartera,
    SnapshotFuenteCartera,
    capturar_snapshot_cartera_desde_entorno,
    guardar_snapshot_cartera,
)
from app.core.usuarios.roles import ROL_SUPER_ADMINISTRADOR
from tests.apoyo_auth import cliente_con_rol, crear_empresa, engine


class ClienteSnapshotFake:
    def obtener_valores(self, *, spreadsheet_id: str, rango: str):
        assert spreadsheet_id == "sheet-cartera"
        assert rango == "FC!A:Z"
        return [
            [
                "NOMBRE",
                "CLIENTE",
                "NUMERO OC",
                "VALOR OCI (DDP)",
                "VALOR ANTICIPO",
                "VALOR FINANCIADO",
                "CARTERA",
            ],
            [
                "Cliente A",
                "Contacto",
                "OC-1",
                "100.10",
                "40.04",
                "60.06",
                "EN CAMINO",
            ],
        ]


def _snapshot() -> SnapshotFuenteCartera:
    return SnapshotFuenteCartera(
        cargado_en=datetime(2026, 9, 29, 20, 0, tzinfo=timezone.utc),
        spreadsheet_id="sheet-cartera",
        rangos={
            "OPERACIONES": "FC!A:Z",
            "MORA": "",
            "PROYECCION": "",
        },
        diagnosticos=(
            {
                "tipo": "OPERACIONES",
                "rango": "FC!A:Z",
                "filas_datos": 1,
                "valido": True,
                "configurado": True,
                "campos_criticos_faltantes": [],
                "encabezados_duplicados": [],
            },
            {
                "tipo": "MORA",
                "rango": "",
                "filas_datos": 0,
                "valido": False,
                "configurado": False,
                "configuracion_faltante": "CARTERA_SHEETS_MORA_RANGE",
                "campos_criticos_faltantes": [],
                "encabezados_duplicados": [],
            },
            {
                "tipo": "PROYECCION",
                "rango": "",
                "filas_datos": 0,
                "valido": False,
                "configurado": False,
                "configuracion_faltante": "CARTERA_SHEETS_PROYECCION_RANGE",
                "campos_criticos_faltantes": [],
                "encabezados_duplicados": [],
            },
        ),
        filas=(
            FilaSnapshotCartera(
                tipo="OPERACIONES",
                fila_fuente=2,
                crudo={
                    "encabezados": ["NUMERO OC", "VALOR OCI (DDP)"],
                    "valores": ["OC-1", "100.10"],
                },
                normalizado={
                    "oc": "OC-1",
                    "valor": "100.10",
                    "valor_anticipo": "40.04",
                    "valor_financiado": "60.06",
                },
            ),
        ),
    )


def test_capture_snapshot_preserves_raw_and_decimal_normalized_values(
    monkeypatch,
) -> None:
    monkeypatch.setenv("CARTERA_SHEETS_EMPRESA_ID", "7")
    monkeypatch.setenv(
        "CARTERA_SHEETS_SPREADSHEET_ID",
        "sheet-cartera",
    )
    monkeypatch.setenv("CARTERA_SHEETS_RANGE", "FC!A:Z")
    monkeypatch.delenv("CARTERA_SHEETS_MORA_RANGE", raising=False)
    monkeypatch.delenv("CARTERA_SHEETS_PROYECCION_RANGE", raising=False)

    snapshot = capturar_snapshot_cartera_desde_entorno(
        empresa_id=7,
        cliente=ClienteSnapshotFake(),
    )

    assert len(snapshot.filas) == 1
    assert snapshot.conteo("OPERACIONES") == 1
    assert snapshot.conteo("MORA") == 0
    assert snapshot.filas[0].fila_fuente == 2
    assert snapshot.filas[0].normalizado["valor"] == "100.10"
    assert snapshot.filas[0].normalizado["valor_anticipo"] == "40.04"
    assert snapshot.filas[0].normalizado["valor_financiado"] == "60.06"


def test_cartera_snapshot_is_append_only_and_idempotent_by_content() -> None:
    empresa_id = crear_empresa("Cartera snapshots")
    snapshot = _snapshot()

    with Session(engine()) as session:
        primero, creado_primero = guardar_snapshot_cartera(
            session,
            empresa_id=empresa_id,
            snapshot=snapshot,
        )
        session.commit()
        snapshot_id = primero.id

    with Session(engine()) as session:
        segundo, creado_segundo = guardar_snapshot_cartera(
            session,
            empresa_id=empresa_id,
            snapshot=snapshot,
        )
        session.commit()

        assert creado_primero is True
        assert creado_segundo is False
        assert segundo.id == snapshot_id

        filas = tuple(
            session.scalars(
                select(CarteraSnapshotFila)
                .where(CarteraSnapshotFila.snapshot_id == snapshot_id)
            )
        )
        assert len(filas) == 1
        assert filas[0].tipo == "OPERACIONES"
        assert filas[0].normalizado["valor"] == "100.10"


def test_api_can_capture_and_list_cartera_snapshots(monkeypatch) -> None:
    empresa_id = crear_empresa("Cartera snapshot API")
    snapshot = _snapshot()
    monkeypatch.setattr(
        cartera_api,
        "capturar_snapshot_cartera_desde_entorno",
        lambda *, empresa_id: snapshot,
    )
    client, _ = cliente_con_rol(ROL_SUPER_ADMINISTRADOR)

    creada = client.post(
        "/api/v1/cartera/snapshots",
        params={"empresa_id": empresa_id},
    )
    listado = client.get(
        "/api/v1/cartera/snapshots",
        params={"empresa_id": empresa_id},
    )

    assert creada.status_code == 201
    body = creada.json()
    assert body["creado"] is True
    assert body["snapshot"]["filas"] == 1
    assert body["snapshot"]["operaciones"] == 1
    assert body["snapshot"]["registros_mora"] == 0
    assert len(body["snapshot"]["contenido_hash"]) == 64

    assert listado.status_code == 200
    lista = listado.json()
    assert lista["total"] >= 1
    assert any(
        item["id"] == body["snapshot"]["id"]
        for item in lista["items"]
    )
