from datetime import date


from app.main import app
from tests.apoyo_auth import cliente_superadmin
from app.motores.cartera_ocs.api import obtener_fuente_proyeccion
from app.motores.cartera_ocs.proyeccion import RegistroProyeccionPago


class FuenteFake:
    def listar(self, *, empresa_id: int):
        assert empresa_id == 3
        return (
            RegistroProyeccionPago(
                cliente="Cliente API",
                contacto="Contacto",
                producto="Producto",
                sku="SKU-P",
                oc="OC-P",
                pais="China",
                estado="En tránsito",
                documento_transporte="BL-P",
                dias=30,
                valor_oc=5000,
                comercial="COMERCIAL API",
                fecha=date(2026, 10, 20),
                monto=2500,
                mes="2026-10",
            ),
        )


def test_web_lists_payment_projection_for_empresa() -> None:
    app.dependency_overrides[obtener_fuente_proyeccion] = lambda: FuenteFake()
    try:
        response = cliente_superadmin().get("/api/v1/cartera/proyeccion?empresa_id=3")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["oc"] == "OC-P"
    assert body[0]["fecha"] == "2026-10-20"
    assert body[0]["monto"] == 2500.0
    assert body[0]["mes"] == "2026-10"
