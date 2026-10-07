"""Regresiones de parejas de archivos y bandeja al reutilizar cargas de Wiilog."""
import io
from datetime import date

import pandas as pd
import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.cargas import Carga
from app.core.hallazgos import Hallazgo
from app.core.periodos import Periodo
from app.motores.conciliacion_wallets.reconciliation_model import WiilogReconciliation
from tests.apoyo_auth import cliente_superadmin
from tests.test_core_wallet_wiilog_vertical_slice import (
    _conciliar, _contexto, _engine, _ordenes_bytes, _wallet_bytes, _xlsx_bytes,
)


@pytest.fixture(autouse=True)
def _runtime_config(monkeypatch):
    monkeypatch.setenv("WIILOG_WALLET_PRINCIPAL_EMAIL", "wallet-principal@wiilog.test")


def _orders_with_extra(order_id):
    rows = pd.read_excel(io.BytesIO(_ordenes_bytes())).to_dict("records")
    rows.append({**rows[1], "ID": order_id, "NÚMERO GUIA": f"G{order_id}"})
    return _xlsx_bytes(rows)


def _wallet_with_review_movement():
    rows = pd.read_excel(io.BytesIO(_wallet_bytes())).to_dict("records")
    rows.append({
        **rows[0], "ID": 2, "FECHA": "11-09-2030 10:00", "MONTO PREVIO": 2500,
        "ORDEN ID": None, "NUMERO DE GUIA": None,
        "DESCRIPCIÓN": "MOVIMIENTO SINTÉTICO POR CLASIFICAR",
    })
    return _xlsx_bytes(rows)


def _findings(client, context, *, history=False):
    response = client.get("/api/v1/wallets/wiilog/hallazgos", params={
        "empresa_id": context[0], "periodo_id": context[1], "todas_las_cargas": history,
    })
    assert response.status_code == 200, response.text
    return response.json()


def test_previously_loaded_files_can_form_a_new_pair_but_not_repeat_it():
    context = _contexto()
    client = cliente_superadmin()
    orders1, orders2 = _ordenes_bytes(), _orders_with_extra(3)
    wallet1, wallet2 = _wallet_bytes(), _wallet_with_review_movement()
    first = _conciliar(client, context, ordenes_bytes=orders1, wallet_bytes=wallet1)
    second = _conciliar(client, context, ordenes_bytes=orders2, wallet_bytes=wallet2)
    assert first.status_code == second.status_code == 201

    crossed = _conciliar(client, context, ordenes_bytes=orders1, wallet_bytes=wallet2)
    assert crossed.status_code == 201, crossed.text
    assert crossed.json()["cargas"]["ordenes_reutilizadas"] is True
    assert crossed.json()["cargas"]["wallet_reutilizada"] is True
    before = _findings(client, context, history=True)

    duplicate = _conciliar(client, context, ordenes_bytes=orders1, wallet_bytes=wallet2)
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Estos archivos ya se conciliaron para este período."
    assert _findings(client, context, history=True) == before


def test_reusing_older_wallet_shows_latest_findings_and_preserves_human_work():
    context = _contexto()
    client = cliente_superadmin()
    wallet1 = _wallet_bytes()
    first = _conciliar(client, context, ordenes_bytes=_ordenes_bytes(), wallet_bytes=wallet1)
    assert first.status_code == 201, first.text
    finding = next(h for h in _findings(client, context) if h["codigo_regla"] == "WIILOG_FF_NO_COBRADO")
    observed = client.post(f"/api/v1/hallazgos/{finding['id']}/observar", json={
        "observacion": "Se conserva la gestión anterior.", "resolver": False,
    })
    assert observed.status_code == 200
    # Representa categorización humana ya persistida, que la sincronización debe conservar.
    category = {"ingreso_egreso": "INGRESO", "unidad_negocio": "FF", "categoria": "COMISIONES"}
    with Session(_engine()) as session:
        row = session.get(Hallazgo, finding["id"])
        row.evidencia = {**row.evidencia, "categorizacion": category}
        session.commit()

    second = _conciliar(client, context, ordenes_bytes=_orders_with_extra(3),
                        wallet_bytes=_wallet_with_review_movement())
    assert second.status_code == 201, second.text
    obsolete = next(h for h in _findings(client, context) if h["evidencia"].get("tipo") == "REVISAR_MOVIMIENTO")

    third = _conciliar(client, context, ordenes_bytes=_orders_with_extra(4), wallet_bytes=wallet1)
    assert third.status_code == 201, third.text
    assert third.json()["cargas"]["wallet_id"] == first.json()["cargas"]["wallet_id"]
    current = _findings(client, context)
    same = next((h for h in current if h["id"] == finding["id"]), None)
    assert same is not None, "La carga antigua ocultó el hallazgo vigente"
    assert same["estado"] == "en_gestion"
    assert same["evidencia"]["categorizacion"] == category
    assert any(h["evidencia"].get("orden_id") == "4" for h in current)
    assert obsolete["id"] not in {h["id"] for h in current}
    historical = next(h for h in _findings(client, context, history=True) if h["id"] == obsolete["id"])
    assert historical["estado"] == "resuelto"
    assert historical["resuelto_por_sistema"] is True


def test_execution_without_findings_clears_inbox_and_remembers_pair():
    context = _contexto()
    client = cliente_superadmin()
    wallet = _wallet_bytes()
    first = _conciliar(client, context, wallet_bytes=wallet)
    assert first.status_code == 201
    assert _findings(client, context)
    # Un único día y una única orden cobrada: sin advertencia de cobertura ni FF pendiente.
    with Session(_engine()) as session:
        period = session.get(Periodo, context[1])
        period.fecha_inicio = date(2030, 9, 10)
        session.commit()
    rows = pd.read_excel(io.BytesIO(_ordenes_bytes())).to_dict("records")
    orders = _xlsx_bytes(rows[:1])
    second = _conciliar(client, context, ordenes_bytes=orders, wallet_bytes=wallet)
    assert second.status_code == 201, second.text
    assert second.json()["hallazgos_creados"] == 0
    assert _findings(client, context) == []
    assert _findings(client, context, history=True)
    assert _conciliar(client, context, ordenes_bytes=orders, wallet_bytes=wallet).status_code == 409


def test_legacy_pair_is_recorded_once_without_inventing_prior_executions():
    context = _contexto()
    client = cliente_superadmin()
    orders, wallet = _ordenes_bytes(), _wallet_bytes()
    first = _conciliar(client, context, ordenes_bytes=orders, wallet_bytes=wallet)
    assert first.status_code == 201
    # Estado anterior a 0019: cargas y hallazgos sin registro de ejecución.
    with Session(_engine()) as session:
        session.execute(delete(WiilogReconciliation).where(WiilogReconciliation.periodo_id == context[1]))
        for finding in session.scalars(select(Hallazgo).where(Hallazgo.periodo_id == context[1])):
            finding.evidencia = {k: v for k, v in finding.evidencia.items() if k != "conciliacion_id"}
        session.commit()
    before = _findings(client, context)
    assert before
    rerun = _conciliar(client, context, ordenes_bytes=orders, wallet_bytes=wallet)
    assert rerun.status_code == 201, rerun.text
    assert {h["id"] for h in _findings(client, context)} == {h["id"] for h in before}
    assert _conciliar(client, context, ordenes_bytes=orders, wallet_bytes=wallet).status_code == 409


def test_invalid_file_rolls_back_new_load_and_keeps_current_execution():
    context = _contexto()
    client = cliente_superadmin()
    orders, wallet = _ordenes_bytes(), _wallet_bytes()
    assert _conciliar(client, context, ordenes_bytes=orders, wallet_bytes=wallet).status_code == 201
    before = _findings(client, context, history=True)
    invalid = _conciliar(client, context, ordenes_bytes=b"not-an-excel", wallet_bytes=wallet)
    assert invalid.status_code == 422
    assert _findings(client, context, history=True) == before
    with Session(_engine()) as session:
        assert session.scalar(select(func.count()).select_from(Carga).where(Carga.empresa_id == context[0])) == 2
        assert session.scalar(select(func.count()).select_from(WiilogReconciliation).where(
            WiilogReconciliation.periodo_id == context[1])) == 1


def test_c0_blocked_execution_does_not_resolve_unevaluated_findings():
    context = _contexto()
    client = cliente_superadmin()
    orders = _ordenes_bytes()
    assert _conciliar(client, context, ordenes_bytes=orders).status_code == 201
    pending = next(h for h in _findings(client, context) if h["codigo_regla"] == "WIILOG_FF_NO_COBRADO")
    rows = pd.read_excel(io.BytesIO(_wallet_with_review_movement())).to_dict("records")
    rows[1]["MONTO PREVIO"] = 99999
    wallet = _xlsx_bytes(rows)
    blocked = _conciliar(client, context, ordenes_bytes=orders, wallet_bytes=wallet)
    assert blocked.status_code == 201, blocked.text
    assert blocked.json()["bloqueado"] is True
    assert all(h["codigo_regla"].startswith("WIILOG_C0_") for h in _findings(client, context))
    old = next(h for h in _findings(client, context, history=True) if h["id"] == pending["id"])
    assert old["estado"] == "detectado"
    assert _conciliar(client, context, ordenes_bytes=orders, wallet_bytes=wallet).status_code == 409
