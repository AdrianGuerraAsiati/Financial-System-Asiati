from decimal import Decimal

from app.main import app
from app.motores.cartera_ocs.api import obtener_fuente_operaciones
from app.motores.cartera_ocs.importacion import RegistroCarteraEnCamino
from tests.apoyo_auth import cliente_superadmin


class FuenteCalidadFake:
    def listar(self, *, empresa_id: int):
        assert empresa_id == 3
        return (
            RegistroCarteraEnCamino(
                cliente="Cliente A",
                contacto="Contacto",
                producto="Producto",
                sku="SKU-1",
                oc="",
                negociacion="",
                modo_transporte="",
                documento_transporte="DOC-1",
                estado="",
                anio_oc=None,
                eta="",
                etapa="EN CAMINO",
                valor=Decimal("100.00"),
                valor_anticipo=Decimal("40.00"),
                valor_financiado=Decimal("50.00"),
                porcentaje_anticipo=Decimal("0.4"),
            ),
        )


def test_web_exposes_existing_cartera_quality_rules() -> None:
    app.dependency_overrides[obtener_fuente_operaciones] = (
        lambda: FuenteCalidadFake()
    )
    try:
        response = cliente_superadmin().get(
            "/api/v1/cartera/calidad?empresa_id=3"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["registros"] == 1
    assert body["casos"] == 2
    assert [item["codigo"] for item in body["detalle"]] == [
        "sin_numero_oc",
        "valor_oci_descuadra",
    ]
    assert body["detalle"][0]["cantidad"] == 1
    assert body["detalle"][0]["valor"] == "100.00"
    assert body["detalle"][1]["valor"] == "10.00"
    assert body["detalle"][0]["registros"][0]["valor"] == "100.00"
