import io
import os
from datetime import date

import pandas as pd
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.cargas import Carga
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
    assert body["c0"]["cuadra"] is True
    assert {"saldo_inicial", "entradas", "salidas", "saldo_final"} <= set(body["c0"])
    assert body["cargas"]["ordenes_id"] > 0
    assert body["cargas"]["wallet_id"] > 0
    assert body["hallazgos_creados"] >= 1
    assert body["hallazgos_por_gravedad"]["CRITICO"] >= 1
    assert sum(body["hallazgos_por_gravedad"].values()) == body["hallazgos_creados"]

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
    assert no_cobrado["gravedad"] == "CRITICO"
    assert no_cobrado["estado"] == "detectado"
    assert no_cobrado["evidencia"]["gravedad"] == "CRITICO"
    assert no_cobrado["evidencia"]["orden_id"] == "2"
    assert no_cobrado["evidencia"]["monto_en_juego_c"] == 250000

    duplicate = client.post("/api/v1/wallets/wiilog/conciliar", data=data, files=files)

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Estos archivos ya se conciliaron para este período."


def _conciliar(client, contexto: tuple[int, int, int, int]):
    empresa_id, periodo_id, fuente_ordenes_id, fuente_wallet_id = contexto
    xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return client.post(
        "/api/v1/wallets/wiilog/conciliar",
        data={
            "empresa_id": str(empresa_id),
            "periodo_id": str(periodo_id),
            "fuente_ordenes_id": str(fuente_ordenes_id),
            "fuente_wallet_id": str(fuente_wallet_id),
        },
        files={
            "ordenes": ("ordenes.xlsx", _ordenes_bytes(), xlsx),
            "wallet": ("wallet.xlsx", _wallet_bytes(), xlsx),
        },
    )


def test_wiilog_inbox_reflects_state_after_observation() -> None:
    contexto = _contexto()
    empresa_id, periodo_id, _, _ = contexto
    client = cliente_superadmin()
    assert _conciliar(client, contexto).status_code == 201
    params = {"empresa_id": empresa_id, "periodo_id": periodo_id}
    primero = client.get("/api/v1/wallets/wiilog/hallazgos", params=params).json()[0]

    observado = client.post(
        f"/api/v1/hallazgos/{primero['id']}/observar",
        json={"observacion": "Revisado con la bodega.", "resolver": False},
    )

    assert observado.status_code == 200, observado.text
    items = client.get("/api/v1/wallets/wiilog/hallazgos", params=params).json()
    actual = next(item for item in items if item["id"] == primero["id"])
    assert actual["estado"] == "en_gestion"


def test_wiilog_without_principal_wallet_config_answers_clearly_and_registers_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WIILOG_WALLET_PRINCIPAL_EMAIL", raising=False)
    contexto = _contexto()
    client = cliente_superadmin()

    response = _conciliar(client, contexto)

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Falta configurar la wallet principal de Wiilog. Pide a TI que la defina."
    )
    with Session(_engine()) as session:
        cargas = session.scalar(
            select(func.count()).select_from(Carga).where(Carga.empresa_id == contexto[0])
        )
    assert cargas == 0


def test_wiilog_review_movement_evidence_has_dropi_text_and_common_catalog() -> None:
    empresa_id, periodo_id, fuente_ordenes_id, fuente_wallet_id = _contexto()
    client = cliente_superadmin()
    texto = "ENTRADA POR RETIRO ADMIN EN USER cliente@x.test"
    wallet = _xlsx_bytes(
        [
            {
                "ID": 1, "FECHA": "10-09-2030 10:00", "TIPO": "ENTRADA", "MONTO": 2500, "MONTO PREVIO": 0,
                "ORDEN ID": 1, "NUMERO DE GUIA": "G1",
                "DESCRIPCIÓN": (
                    "PAGO POR GANANCIA COMISION FULFILLMENT DE MARCA BLANCA. "
                    "ORDEN ID *1* GUIA: *G1* CONCEPTO: GUIA_GENERADA"
                ),
                "USUARIO QUE REALIZA EL MOVIMIENTO": "", "CUENTA": None, "CONCEPTO DE RETIRO": None,
            },
            {
                "ID": 2, "FECHA": "11-09-2030 10:00", "TIPO": "ENTRADA", "MONTO": 7000, "MONTO PREVIO": 2500,
                "ORDEN ID": None, "NUMERO DE GUIA": None, "DESCRIPCIÓN": texto,
                "USUARIO QUE REALIZA EL MOVIMIENTO": "", "CUENTA": None, "CONCEPTO DE RETIRO": None,
            },
        ]
    )
    xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    response = client.post(
        "/api/v1/wallets/wiilog/conciliar",
        data={
            "empresa_id": str(empresa_id),
            "periodo_id": str(periodo_id),
            "fuente_ordenes_id": str(fuente_ordenes_id),
            "fuente_wallet_id": str(fuente_wallet_id),
        },
        files={
            "ordenes": ("ordenes.xlsx", _ordenes_bytes(), xlsx),
            "wallet": ("wallet.xlsx", wallet, xlsx),
        },
    )

    assert response.status_code == 201, response.text
    items = client.get(
        "/api/v1/wallets/wiilog/hallazgos",
        params={"empresa_id": empresa_id, "periodo_id": periodo_id},
    ).json()
    [revisar] = [i for i in items if i["codigo_regla"] == "WIILOG_MOVIMIENTO_REVISAR"]
    evidencia = revisar["evidencia"]
    assert evidencia["tipo"] == "REVISAR_MOVIMIENTO"
    assert evidencia["texto_dropi"] == texto
    assert evidencia["entrada_salida"] == "ENTRADA"
    assert evidencia["monto"] == "7000.00"
    assert evidencia["texto_nuevo"] is False
    assert (evidencia["ingreso_egreso"], evidencia["unidad_negocio"], evidencia["categoria"]) == ("INGRESO", None, None)



def test_wiilog_reconciling_with_a_new_file_keeps_state_and_same_finding() -> None:
    contexto = _contexto()
    empresa_id, periodo_id, fuente_ordenes_id, fuente_wallet_id = contexto
    client = cliente_superadmin()
    assert _conciliar(client, contexto).status_code == 201
    params = {"empresa_id": empresa_id, "periodo_id": periodo_id}
    no_cobrado = next(
        h for h in client.get("/api/v1/wallets/wiilog/hallazgos", params=params).json()
        if h["codigo_regla"] == "WIILOG_FF_NO_COBRADO"
    )
    client.post(
        f"/api/v1/hallazgos/{no_cobrado['id']}/observar",
        json={"observacion": "Se reclama a la bodega.", "resolver": False},
    )
    # Exportaciones nuevas de Dropi: un movimiento y una orden más; el problema de la orden 2 sigue.
    filas = pd.read_excel(io.BytesIO(_wallet_bytes())).to_dict("records")
    filas.append({**filas[0], "ID": 2, "FECHA": "11-09-2030 10:00", "MONTO PREVIO": 2500})
    ordenes = pd.read_excel(io.BytesIO(_ordenes_bytes())).to_dict("records")
    ordenes.append({**ordenes[1], "ID": 3, "NÚMERO GUIA": "G3"})
    xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    segunda = client.post(
        "/api/v1/wallets/wiilog/conciliar",
        data={
            "empresa_id": str(empresa_id),
            "periodo_id": str(periodo_id),
            "fuente_ordenes_id": str(fuente_ordenes_id),
            "fuente_wallet_id": str(fuente_wallet_id),
        },
        files={
            "ordenes": ("ordenes_2.xlsx", _xlsx_bytes(ordenes), xlsx),
            "wallet": ("wallet_2.xlsx", _xlsx_bytes(filas), xlsx),
        },
    )

    assert segunda.status_code == 201, segunda.text
    despues = next(
        h for h in client.get("/api/v1/wallets/wiilog/hallazgos", params=params).json()
        if h["codigo_regla"] == "WIILOG_FF_NO_COBRADO" and h["evidencia"]["orden_id"] == "2"
    )
    assert despues["id"] == no_cobrado["id"]
    assert despues["estado"] == "en_gestion"
    assert despues["evidencia"]["carga_wallet_id"] == segunda.json()["cargas"]["wallet_id"]



def test_wiilog_reuses_the_same_orders_report_with_a_new_wallet() -> None:
    contexto = _contexto()
    empresa_id, periodo_id, fuente_ordenes_id, fuente_wallet_id = contexto
    client = cliente_superadmin()
    primera = _conciliar(client, contexto)
    assert primera.status_code == 201
    filas = pd.read_excel(io.BytesIO(_wallet_bytes())).to_dict("records")
    filas.append({**filas[0], "ID": 2, "FECHA": "11-09-2030 10:00", "MONTO PREVIO": 2500})
    xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    segunda = client.post(
        "/api/v1/wallets/wiilog/conciliar",
        data={
            "empresa_id": str(empresa_id),
            "periodo_id": str(periodo_id),
            "fuente_ordenes_id": str(fuente_ordenes_id),
            "fuente_wallet_id": str(fuente_wallet_id),
        },
        files={
            "ordenes": ("ordenes.xlsx", _ordenes_bytes(), xlsx),
            "wallet": ("wallet_nueva.xlsx", _xlsx_bytes(filas), xlsx),
        },
    )

    assert segunda.status_code == 201, segunda.text
    cargas = segunda.json()["cargas"]
    assert cargas["ordenes_reutilizadas"] is True
    assert cargas["ordenes_id"] == primera.json()["cargas"]["ordenes_id"]
    assert cargas["wallet_reutilizada"] is False
