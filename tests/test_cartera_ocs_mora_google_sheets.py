from decimal import Decimal

from app.motores.cartera_ocs.google_sheets import FuenteMoraGoogleSheets


class LectorFake:
    def leer_filas(self, *, empresa_id: int):
        assert empresa_id == 7
        return [
            {
                "Cliente": "Cliente Mora",
                "Empresa / Subtítulo": "ASIATI Comercial",
                "Monto en mora (USD)": "4.300,00",
                "Observación más reciente": "Pendiente pago",
                "CARTERA": "mora",
            },
            {
                "Cliente": "",
                "Monto en mora (USD)": "100",
                "CARTERA": "MORA",
            },
        ]


def test_google_sheets_adapter_normalizes_mora_rows() -> None:
    fuente = FuenteMoraGoogleSheets(LectorFake())

    registros = fuente.listar(empresa_id=7)

    assert len(registros) == 1
    assert registros[0].cliente == "Cliente Mora"
    assert registros[0].empresa == "ASIATI Comercial"
    assert registros[0].monto == Decimal("4300.00")
    assert registros[0].estado == "MORA"
