from app.motores.cartera_ocs.google_sheets import (
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
    assert operaciones[0].valor == 10000
