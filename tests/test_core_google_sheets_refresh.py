from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.google_sheets.model import SourceRefreshState
from app.integrations.google_sheets.service import (
    reclamar_refresco_si_corresponde,
    registrar_cambio,
)
from tests.apoyo_auth import cliente, crear_empresa, engine


def test_change_webhook_coalesces_events_without_reading_google(monkeypatch) -> None:
    empresa_id = crear_empresa("Webhook Sheets")
    monkeypatch.setenv("GOOGLE_SHEETS_CHANGE_SECRET", "secret-test")
    monkeypatch.setenv("CARTERA_SHEETS_SPREADSHEET_ID", "sheet-cartera")

    client = cliente()
    payload = {
        "modulo": "cartera",
        "empresa_id": empresa_id,
        "spreadsheet_id": "sheet-cartera",
        "hoja": "MORA",
        "rango": "C12",
        "tipo_evento": "EDIT",
    }
    headers = {"X-ASIATI-Sheet-Secret": "secret-test"}

    primera = client.post(
        "/api/v1/integrations/google-sheets/changed",
        json=payload,
        headers=headers,
    )
    segunda = client.post(
        "/api/v1/integrations/google-sheets/changed",
        json={**payload, "rango": "C13"},
        headers=headers,
    )

    assert primera.status_code == 202
    assert segunda.status_code == 202

    with Session(engine()) as session:
        estado = session.scalar(
            select(SourceRefreshState).where(
                SourceRefreshState.empresa_id == empresa_id,
                SourceRefreshState.modulo == "cartera",
            )
        )
        assert estado is not None
        assert estado.estado == "PENDING"
        assert estado.event_count == 2
        assert estado.first_event_at is not None
        assert estado.last_event_at is not None


def test_change_webhook_rejects_wrong_secret(monkeypatch) -> None:
    empresa_id = crear_empresa("Webhook Sheets secret")
    monkeypatch.setenv("GOOGLE_SHEETS_CHANGE_SECRET", "secret-test")
    monkeypatch.setenv("CARTERA_SHEETS_SPREADSHEET_ID", "sheet-cartera")

    response = cliente().post(
        "/api/v1/integrations/google-sheets/changed",
        json={
            "modulo": "cartera",
            "empresa_id": empresa_id,
            "spreadsheet_id": "sheet-cartera",
        },
        headers={"X-ASIATI-Sheet-Secret": "incorrecto"},
    )

    assert response.status_code == 401


def test_debounce_waits_for_quiet_period_and_claims_once(monkeypatch) -> None:
    empresa_id = crear_empresa("Debounce Sheets")
    monkeypatch.setenv("GOOGLE_SHEETS_DEBOUNCE_SECONDS", "15")
    monkeypatch.setenv("GOOGLE_SHEETS_MAX_WAIT_SECONDS", "60")
    ahora = datetime(2026, 9, 29, 20, 0, tzinfo=timezone.utc)

    with Session(engine()) as session:
        registrar_cambio(
            session,
            empresa_id=empresa_id,
            modulo="cartera",
            ahora=ahora,
        )
        session.commit()

    with Session(engine()) as session:
        temprano = reclamar_refresco_si_corresponde(
            session,
            empresa_id=empresa_id,
            modulo="cartera",
            ahora=ahora + timedelta(seconds=14),
        )
        session.commit()
        assert temprano is None

    with Session(engine()) as session:
        corte = reclamar_refresco_si_corresponde(
            session,
            empresa_id=empresa_id,
            modulo="cartera",
            ahora=ahora + timedelta(seconds=15),
        )
        session.commit()
        assert corte == ahora

    with Session(engine()) as session:
        estado = session.scalar(
            select(SourceRefreshState).where(
                SourceRefreshState.empresa_id == empresa_id,
                SourceRefreshState.modulo == "cartera",
            )
        )
        assert estado is not None
        assert estado.estado == "REFRESHING"
