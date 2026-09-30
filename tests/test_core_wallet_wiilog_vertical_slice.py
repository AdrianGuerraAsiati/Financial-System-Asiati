import io
import os
from datetime import date

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.empresas import Empresa
from app.core.fuentes import Fuente
from app.core.periodos import Periodo
from app.main import app
from tests.apoyo_auth import cliente_superadmin


@pytest.fixture(autouse=True)
def _wiilog_runtime_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "WIILOG_WALLET_PRINCIPAL_EMAIL",
        "wallet-principal@wiilog.test",
    )


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def _xlsx_bytes(rows: list[dict[str, object]]) -> bytes:
    buffer = io.BytesIO()
    pd.DataFrame(rows).to_excel(buffer, index=False)
    return buffer.getvalue()


def _wallet_bytes() -> bytes:
    return _xlsx_bytes(
        [
            {
                "ID": 1,
                "FECHA": "10-09-2030 10:00",
                "TIPO": "ENTRADA",
                "MONTO": 2500,
                "MONTO PREVIO": 0,
                "ORDEN ID": 1,
                "NUMERO DE GUIA": "G1",
                "DESCRIPCIÓN": (
                    "PAGO POR GANANCIA COMISION FULFILLMENT DE MARCA BLANCA. "
                    "ORDEN ID *1* GUIA: *G1* CONCEPTO: GUIA_GENERADA"
                ),
                "USUARIO QUE REALIZA EL MOVIMIENTO": "",
                "CUENTA": None,
                "CONCEPTO DE RETIRO": None,
            }
        ]
    )


def _ordenes_bytes() -> bytes:
    return _xlsx_bytes(
        [
            {
                "ID": 1,
                "NÚMERO GUIA": "G1",
                "ESTATUS": "GUIA_GENERADA",
                "TIPO DE ENVIO": "CON RECAUDO",
                "TRANSPORTADORA": "ENVIA",
                "BODEGA": "WIILOG BOGOTÁ",
                "ID DE BODEGA": 1,
                "FECHA": "09-09-2030",
                "FECHA GENERACION DE GUIA": "10/09/2030",
                "FECHA ENTREGADO": None,
                "FECHA DEVOLUCION": None,
            },
            {
                "ID": 2,
                "NÚMERO GUIA": "G2",
                "ESTATUS": "GUIA_GENERADA",
                "TIPO DE ENVIO": "CON RECAUDO",
                "TRANSPORTADORA": "ENVIA",
                "BODEGA": "WIILOG BOGOTÁ",
                "ID DE BODEGA": 1,
                "FECHA": "01-09-2030",
                "FECHA GENERACION DE GUIA": "01/09/2030",
                "FECHA ENTREGADO": None,
                "FECHA DEVOLUCION": None,
            },
        ]
    )


def _contexto() -> tuple[int, int, int, int]:
    engine = _engine()
    with Session(engine) as session:
        empresa = Empresa(nombre="Wiilog vertical slice")
        session.add(empresa)
        session.flush()

        fuente_ordenes = Fuente(
            empresa_id=empresa.id,
            nombre="Dropi órdenes Wiilog",
        )
        fuente_wallet = Fuente(
            empresa_id=empresa.id,
            nombre="Dropi wallet Wiilog",
        )
        periodo = Periodo(
            empresa_id=empresa.id,
            fecha_inicio=date(2030, 9, 1),
            fecha_fin=date(2030, 9, 30),
        )
        session.add_all([fuente_ordenes, fuente_wallet, periodo])
        session.commit()

        return (
            empresa.id,
            periodo.id,
            fuente_ordenes.id,
            fuente_wallet.id,
        )


def test_wiilog_vertical_slice_persists_findings_and_rejects_duplicate_loads() -> None:
    empresa_id, periodo_id, fuente_ordenes_id, fuente_wallet_id = _contexto()
    client = cliente_superadmin()

    data = {
        "empresa_id": str(empresa_id),
        "periodo_id": str(periodo_id),
        "fuente_ordenes_id": str(fuente_ordenes_id),
        "fuente_wallet_id": str(fuente_wallet_id),
    }
    files = {
        "ordenes": (
            "ordenes.xlsx",
            _ordenes_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        "wallet": (
            "wallet.xlsx",
            _wallet_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    }

    response = client.post("/api/v1/wallets/wiilog/conciliar", data=data, files=files)

    assert response.status_code == 201
    body = response.json()
    assert body["bloqueado"] is False
    assert body["cargas"]["ordenes_id"] > 0
    assert body["cargas"]["wallet_id"] > 0
    assert body["hallazgos_creados"] >= 1

    hallazgos = client.get(
        "/api/v1/wallets/wiilog/hallazgos",
        params={"empresa_id": empresa_id, "periodo_id": periodo_id},
    )

    assert hallazgos.status_code == 200
    items = hallazgos.json()
    no_cobrado = next(
        item for item in items
        if item["codigo_regla"] == "WIILOG_FF_NO_COBRADO"
    )
    assert no_cobrado["critico"] is True
    assert no_cobrado["evidencia"]["orden_id"] == "2"
    assert no_cobrado["evidencia"]["monto_en_juego_c"] == 250000

    duplicate = client.post("/api/v1/wallets/wiilog/conciliar", data=data, files=files)

    assert duplicate.status_code == 409
    assert "ya fue cargado" in duplicate.json()["detail"].lower()
