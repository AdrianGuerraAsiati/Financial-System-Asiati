import pytest

from app.motores.compras_supply_chain.google_sheets import (
    ConfiguracionComprasGoogleSheetsError,
    construir_fuente_compras_desde_entorno,
)


def test_compras_demo_mode_builds_without_google_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("COMPRAS_DEMO_MODE", "true")
    monkeypatch.setenv("COMPRAS_SHEETS_EMPRESA_ID", "1")
    monkeypatch.delenv("COMPRAS_SHEETS_SPREADSHEET_ID", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)

    fuente = construir_fuente_compras_desde_entorno()
    snapshot = fuente.obtener_snapshot(empresa_id=1)

    assert fuente.configuracion.modo_fuente == "DEMO_LOCAL"
    assert snapshot.esquema_valido is True
    assert len(snapshot.lineas) == 9
    assert {linea.pais for linea in snapshot.lineas} == {"CO", "EC", "CL"}
    assert any(linea.numero_oc == "OC-CO-1001" for linea in snapshot.lineas)


def test_compras_demo_mode_is_rejected_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("COMPRAS_DEMO_MODE", "true")

    with pytest.raises(
        ConfiguracionComprasGoogleSheetsError,
        match="no puede usarse en producción",
    ):
        construir_fuente_compras_desde_entorno()


def test_compras_demo_source_keeps_monetary_columns_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("COMPRAS_DEMO_MODE", "true")
    monkeypatch.setenv("COMPRAS_SHEETS_EMPRESA_ID", "1")

    fuente = construir_fuente_compras_desde_entorno()
    snapshot = fuente.obtener_snapshot(empresa_id=1)

    for diagnostico in snapshot.diagnosticos:
        assert "valor_total_compra_usd" in diagnostico.campos_reconocidos
        assert "valor_oci_ddp" in diagnostico.campos_reconocidos
