from fastapi.testclient import TestClient

from app.main import app
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
                valor=5000,
                valor_anticipo=2000,
                valor_financiado=3000,
                porcentaje_anticipo=0.4,
            ),
        )


def test_web_lists_operations_for_empresa() -> None:
    app.dependency_overrides[obtener_fuente_operaciones] = lambda: FuenteFake()
    try:
        response = TestClient(app).get("/cartera/operaciones?empresa_id=3")
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
            "valor": 5000.0,
            "valor_anticipo": 2000.0,
            "valor_financiado": 3000.0,
            "porcentaje_anticipo": 0.4,
        }
    ]
