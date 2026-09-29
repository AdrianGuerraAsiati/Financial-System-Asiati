
from decimal import Decimal

from app.main import app
from tests.apoyo_auth import cliente_superadmin
from app.motores.cartera_ocs.api import obtener_fuente_operaciones
from app.motores.cartera_ocs.importacion import RegistroCarteraEnCamino


class FuenteFake:
    def listar(self, *, empresa_id: int):
        assert empresa_id == 3
        return (
            RegistroCarteraEnCamino(
                cliente="Cliente Web",
                contacto="Contacto",
                producto="Producto",
                sku="SKU-W",
                oc="OC-WEB",
                negociacion="Crédito",
                modo_transporte="Marítimo",
                documento_transporte="BL-1",
                estado="Entregado",
                anio_oc=2026,
                eta="2026-10-01",
                etapa="EN CAMINO",
                valor=Decimal("5000.00"),
                valor_anticipo=Decimal("2000.00"),
                valor_financiado=Decimal("3000.00"),
                porcentaje_anticipo=Decimal("0.4"),
            ),
        )


def test_web_lists_operations_for_empresa() -> None:
    app.dependency_overrides[obtener_fuente_operaciones] = lambda: FuenteFake()
    try:
        response = cliente_superadmin().get("/api/v1/cartera/operaciones?empresa_id=3")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == [
        {
            "oc": "OC-WEB",
            "cliente": "Cliente Web",
            "contacto": "Contacto",
            "producto": "Producto",
            "sku": "SKU-W",
            "negociacion": "Crédito",
            "modo_transporte": "Marítimo",
            "documento_transporte": "BL-1",
            "estado": "Entregado",
            "anio_oc": 2026,
            "eta": "2026-10-01",
            "etapa": "EN CAMINO",
            "valor": "5000.00",
            "valor_anticipo": "2000.00",
            "valor_financiado": "3000.00",
            "porcentaje_anticipo": "0.4",
        }
    ]
