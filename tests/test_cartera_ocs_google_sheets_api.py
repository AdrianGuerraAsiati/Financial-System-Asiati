from decimal import Decimal

from app.motores.cartera_ocs import google_sheets as google_sheets_mod
from app.motores.cartera_ocs.google_sheets import (
    CLOUD_PLATFORM_SCOPE,
    SHEETS_READONLY_SCOPE,
    ClienteGoogleSheetsApi,
    ConfiguracionGoogleSheets,
    LectorGoogleSheetsApi,
    construir_fuente_google_sheets_desde_entorno,
)


class RespuestaFake:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self.body


class SesionFake:
    def __init__(self, body):
        self.body = body
        self.url = None

    def get(self, url, timeout):
        self.url = url
        assert timeout == 30
        return RespuestaFake(self.body)


class ClienteFake:
    def obtener_valores(self, *, spreadsheet_id: str, rango: str):
        assert spreadsheet_id == "sheet-123"
        assert rango == "FC!A:Z"
        return [
            ["NOMBRE", "CLIENTE", "NUMERO OC", "VALOR OCI (DDP)", "CARTERA"],
            ["Cliente A", "Contacto A", "OC-1", "10.000,00", "2. EN CAMINO"],
        ]


def test_google_api_client_requests_values_endpoint() -> None:
    session = SesionFake({"values": [["NOMBRE"], ["Cliente A"]]})
    client = ClienteGoogleSheetsApi(session=session)

    values = client.obtener_valores(
        spreadsheet_id="sheet 123",
        rango="FC!A:Z",
    )

    assert values == [["NOMBRE"], ["Cliente A"]]
    assert session.url == (
        "https://sheets.googleapis.com/v4/spreadsheets/"
        "sheet%20123/values/FC%21A%3AZ?majorDimension=ROWS"
    )


def test_reader_maps_header_row_to_operation_rows() -> None:
    reader = LectorGoogleSheetsApi(
        cliente=ClienteFake(),
        configuraciones={
            7: ConfiguracionGoogleSheets(
                spreadsheet_id="sheet-123",
                rango="FC!A:Z",
            )
        },
    )

    rows = list(reader.leer_filas(empresa_id=7))

    assert rows == [
        {
            "NOMBRE": "Cliente A",
            "CLIENTE": "Contacto A",
            "NUMERO OC": "OC-1",
            "VALOR OCI (DDP)": "10.000,00",
            "CARTERA": "2. EN CAMINO",
        }
    ]


def test_environment_builds_google_sheets_source(monkeypatch) -> None:
    monkeypatch.setenv("CARTERA_SHEETS_EMPRESA_ID", "7")
    monkeypatch.setenv("CARTERA_SHEETS_SPREADSHEET_ID", "sheet-123")
    monkeypatch.setenv("CARTERA_SHEETS_RANGE", "FC!A:Z")

    fuente = construir_fuente_google_sheets_desde_entorno(
        cliente=ClienteFake(),
    )

    operaciones = fuente.listar(empresa_id=7)

    assert len(operaciones) == 1
    assert operaciones[0].oc == "OC-1"
    assert operaciones[0].valor == Decimal("10000.00")


def test_google_api_client_supports_keyless_impersonation(monkeypatch) -> None:
    source_credentials = object()
    impersonated = object()
    captured = {}

    def fake_default(*, scopes):
        captured["source_scopes"] = scopes
        return source_credentials, "project"

    def fake_impersonated_credentials(**kwargs):
        captured["impersonation"] = kwargs
        return impersonated

    class FakeAuthorizedSession:
        def __init__(self, credentials):
            captured["session_credentials"] = credentials

    monkeypatch.setattr(google_sheets_mod.google.auth, "default", fake_default)
    monkeypatch.setattr(
        google_sheets_mod.impersonated_credentials,
        "Credentials",
        fake_impersonated_credentials,
    )
    monkeypatch.setattr(
        google_sheets_mod,
        "AuthorizedSession",
        FakeAuthorizedSession,
    )

    ClienteGoogleSheetsApi(
        target_principal="financial-system@project.iam.gserviceaccount.com"
    )

    assert captured["source_scopes"] == [CLOUD_PLATFORM_SCOPE]
    assert captured["impersonation"] == {
        "source_credentials": source_credentials,
        "target_principal": "financial-system@project.iam.gserviceaccount.com",
        "target_scopes": [SHEETS_READONLY_SCOPE],
        "lifetime": 3600,
    }
    assert captured["session_credentials"] is impersonated
