
from app.main import app
from tests.apoyo_auth import cliente_superadmin
from app.motores.cartera_ocs.api import obtener_fuente_operaciones
from app.motores.cartera_ocs.importacion import RegistroCarteraEnCamino


def _registro(sku: str) -> RegistroCarteraEnCamino:
    return RegistroCarteraEnCamino(
        cliente="Cliente Detalle",
        contacto="Contacto",
        producto=f"Producto {sku}",
        sku=sku,
        oc="OC-DET",
        negociacion="50% anticipo / 50% a la entrega",
        modo_transporte="Aéreo",
        documento_transporte="GUIA-1",
        estado="Entregado",
        anio_oc=2026,
        eta="2026-09-28",
        etapa="EN CAMINO",
        valor=500,
        valor_anticipo=250,
        valor_financiado=250,
        porcentaje_anticipo=0.5,
    )


class FuenteFake:
    def listar(self, *, empresa_id: int):
        return (_registro("SKU-1"), _registro("SKU-2"))


def test_web_returns_individual_operation_with_all_lines() -> None:
    app.dependency_overrides[obtener_fuente_operaciones] = lambda: FuenteFake()
    try:
        response = cliente_superadmin().get(
            "/api/v1/cartera/operaciones/OC-DET?empresa_id=4"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["oc"] == "OC-DET"
    assert len(body["lineas"]) == 2
    assert [linea["sku"] for linea in body["lineas"]] == ["SKU-1", "SKU-2"]


def test_web_returns_404_for_unknown_operation() -> None:
    app.dependency_overrides[obtener_fuente_operaciones] = lambda: FuenteFake()
    try:
        response = cliente_superadmin().get(
            "/api/v1/cartera/operaciones/OC-X?empresa_id=4"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
