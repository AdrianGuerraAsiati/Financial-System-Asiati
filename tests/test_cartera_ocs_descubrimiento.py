from app.motores.cartera_ocs.descubrimiento import (
    descubrir_hojas_cartera_desde_entorno,
)


class ClienteDescubrimientoFake:
    def __init__(self) -> None:
        self.rangos = []

    def obtener_hojas(self, *, spreadsheet_id: str):
        assert spreadsheet_id == "sheet-cartera"
        return (
            "Inicio",
            "FC",
            "MORA",
            "PROYECCIONES",
        )

    def obtener_valores(self, *, spreadsheet_id: str, rango: str):
        assert spreadsheet_id == "sheet-cartera"
        self.rangos.append(rango)

        if rango == "'Inicio'!A1:ZZ20":
            return [["Dashboard"], ["Sin contrato"]]
        if rango == "'FC'!A1:ZZ20":
            return [
                ["Título"],
                [],
                [
                    "NOMBRE",
                    "NUMERO OC",
                    "VALOR OCI (DDP)",
                    "CARTERA",
                ],
                ["Cliente A", "OC-1", "100.00", "EN CAMINO"],
            ]
        if rango == "'MORA'!A1:ZZ20":
            return [
                [
                    "Cliente",
                    "Monto en mora (USD)",
                    "CARTERA",
                ],
                ["Cliente A", "20.00", "MORA"],
            ]
        if rango == "'PROYECCIONES'!A1:ZZ20":
            return [
                ["Título"],
                [
                    "NUMERO OC",
                    "FECHA DE PAGO ESPERADA",
                    "MONTO ESPERADO",
                ],
                ["OC-1", "2026-10-15", "50.00"],
            ]
        raise AssertionError(rango)


def test_discovers_exact_cartera_contracts_without_guessing(monkeypatch) -> None:
    monkeypatch.setenv("CARTERA_SHEETS_EMPRESA_ID", "7")
    monkeypatch.setenv(
        "CARTERA_SHEETS_SPREADSHEET_ID",
        "sheet-cartera",
    )

    resultado = descubrir_hojas_cartera_desde_entorno(
        empresa_id=7,
        cliente=ClienteDescubrimientoFake(),
    )

    assert resultado["coincidencias_exactas"] == 3

    exactas = {
        item["tipo"]: item
        for hoja in resultado["hojas"]
        for item in hoja["candidatos"]
        if item["coincide"] is True
    }
    assert exactas["OPERACIONES"]["fila_encabezado"] == 3
    assert exactas["OPERACIONES"]["rango_sugerido"] == "'FC'!A3:ZZ"
    assert exactas["MORA"]["rango_sugerido"] == "'MORA'!A1:ZZ"
    assert (
        exactas["PROYECCION"]["rango_sugerido"]
        == "'PROYECCIONES'!A2:ZZ"
    )


def test_sheet_title_is_escaped_in_suggested_a1_range(monkeypatch) -> None:
    monkeypatch.setenv("CARTERA_SHEETS_EMPRESA_ID", "7")
    monkeypatch.setenv(
        "CARTERA_SHEETS_SPREADSHEET_ID",
        "sheet-cartera",
    )

    class ClienteApostrofe:
        def obtener_hojas(self, *, spreadsheet_id: str):
            return ("Cartera O'Brien",)

        def obtener_valores(self, *, spreadsheet_id: str, rango: str):
            assert rango == "'Cartera O''Brien'!A1:ZZ20"
            return [[
                "NUMERO OC",
                "VALOR OCI (DDP)",
                "CARTERA",
            ]]

    resultado = descubrir_hojas_cartera_desde_entorno(
        empresa_id=7,
        cliente=ClienteApostrofe(),
    )

    candidato = resultado["hojas"][0]["candidatos"][0]
    assert candidato["rango_sugerido"] == "'Cartera O''Brien'!A1:ZZ"
