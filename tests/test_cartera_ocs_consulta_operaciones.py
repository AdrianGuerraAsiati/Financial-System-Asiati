from app.motores.cartera_ocs.consultas import listar_operaciones
from app.motores.cartera_ocs.google_sheets import FuenteOperacionesGoogleSheets


class LectorFake:
    def leer_filas(self, *, empresa_id: int):
        assert empresa_id == 7
        return [
            {
                "NOMBRE": "Cliente A",
                "CLIENTE": "Contacto A",
                "DESCRIPCION": "Producto A",
                "SKU": "SKU-1",
                "NUMERO OC": "OC-1",
                "TIPO DE NEGOCIACION": "50% anticipo / 50% a la entrega",
                "VALOR OCI (DDP)": "10.000,00",
                "MODO TRANSPORTE": "Aéreo",
                "DOCUMENTO DE TRANSPORTE": "GUIA-1",
                "ESTADO": "En tránsito",
                "CARTERA": "2. EN CAMINO",
            },
            {
                "NOMBRE": "TOTAL",
                "CLIENTE": "",
                "SKU": "",
                "NUMERO OC": "",
            },
        ]


def test_google_sheets_adapter_normalizes_rows_and_discards_totals() -> None:
    fuente = FuenteOperacionesGoogleSheets(LectorFake())

    operaciones = listar_operaciones(fuente, empresa_id=7)

    assert len(operaciones) == 1
    assert operaciones[0].oc == "OC-1"
    assert operaciones[0].cliente == "Cliente A"
    assert operaciones[0].valor == 10000
    assert operaciones[0].etapa == "EN CAMINO"
