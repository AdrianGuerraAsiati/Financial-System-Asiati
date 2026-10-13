from datetime import date
from decimal import Decimal

from app.motores.cartera_ocs.google_sheets import FuenteProyeccionGoogleSheets


class LectorFake:
    def leer_filas(self, *, empresa_id: int):
        assert empresa_id == 7
        return [
            {
                "NOMBRE": "Cliente Proyección",
                "CLIENTE": "Contacto",
                "DESCRIPCION": "Producto",
                "SKU": "SKU-1",
                "NUMERO OC": "OC-PROY",
                "PAIS ORIGEN": "China",
                "ESTADO": "En tránsito",
                "DOCUMENTO DE TRANSPORTE": "BL-1",
                "DIAS": "30",
                "VALOR OCI": "10.000,00",
                "FECHA DE PAGO ESPERADA": "2026-10-15",
                "MONTO ESPERADO": "4.300,00",
                "COMERCIAL": "Comercial A",
            },
            {
                "NOMBRE": "Sin monto",
                "FECHA DE PAGO ESPERADA": "2026-10-15",
                "MONTO ESPERADO": "0",
            },
        ]


def test_google_sheets_adapter_normalizes_projection_rows() -> None:
    fuente = FuenteProyeccionGoogleSheets(LectorFake())

    registros = fuente.listar(empresa_id=7)

    assert len(registros) == 1
    assert registros[0].oc == "OC-PROY"
    assert registros[0].cliente == "Cliente Proyección"
    assert registros[0].fecha == date(2026, 10, 15)
    assert registros[0].monto == Decimal("4300.00")
    assert registros[0].valor_oc == Decimal("10000.00")
    assert registros[0].mes == "2026-10"
    assert registros[0].comercial == "COMERCIAL A"
