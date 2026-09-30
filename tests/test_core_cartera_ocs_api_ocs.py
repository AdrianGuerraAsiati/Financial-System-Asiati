from decimal import Decimal

from app.main import app
from app.motores.cartera_ocs.api import obtener_fuente_operaciones
from app.motores.cartera_ocs.importacion import RegistroCarteraEnCamino
from tests.apoyo_auth import cliente_superadmin


class FuenteFake:
    def listar(self, *, empresa_id: int):
        assert empresa_id == 3
        return (
            RegistroCarteraEnCamino(
                cliente="Cliente A",
                contacto="Contacto",
                producto="Producto 1",
                sku="SKU-1",
                oc="OC-1",
                negociacion="50/50",
                modo_transporte="Marítimo",
                documento_transporte="BL-1",
                estado="EN CAMINO",
                anio_oc=2026,
                eta="2026-10-01",
                etapa="EN CAMINO",
                valor=Decimal("100.00"),
                valor_anticipo=Decimal("40.00"),
                valor_financiado=Decimal("60.00"),
                porcentaje_anticipo=Decimal("0.4"),
            ),
            RegistroCarteraEnCamino(
                cliente="Cliente A",
                contacto="Contacto",
                producto="Producto 2",
                sku="SKU-2",
                oc="OC-1",
                negociacion="50/50",
                modo_transporte="Aéreo",
                documento_transporte="AWB-2",
                estado="ENTREGADO",
                anio_oc=2026,
                eta="2026-10-02",
                etapa="ENTREGADO",
                valor=Decimal("50.00"),
                valor_anticipo=Decimal("20.00"),
                valor_financiado=Decimal("30.00"),
                porcentaje_anticipo=Decimal("0.4"),
            ),
            RegistroCarteraEnCamino(
                cliente="Cliente sin OC",
                contacto="",
                producto="",
                sku="",
                oc="",
                negociacion="",
                modo_transporte="",
                documento_transporte="",
                estado="",
                anio_oc=2026,
                eta="",
                etapa="Sin clasificar",
                valor=Decimal("25.00"),
                valor_anticipo=Decimal("0"),
                valor_financiado=Decimal("0"),
                porcentaje_anticipo=Decimal("0"),
            ),
        )


def test_api_lista_ocs_agrupadas_sin_colapsar_composicion() -> None:
    app.dependency_overrides[obtener_fuente_operaciones] = lambda: FuenteFake()
    try:
        response = cliente_superadmin().get(
            "/api/v1/cartera/ocs?empresa_id=3"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["lineas_sin_oc"] == 1
    assert body["items"] == [
        {
            "oc": "OC-1",
            "lineas": 2,
            "clientes": ["Cliente A"],
            "negociaciones": ["50/50"],
            "estados": ["EN CAMINO", "ENTREGADO"],
            "etapas": ["EN CAMINO", "ENTREGADO"],
            "modos_transporte": ["Marítimo", "Aéreo"],
            "documentos_transporte": ["BL-1", "AWB-2"],
            "skus": ["SKU-1", "SKU-2"],
            "valor_ddp": "150.00",
            "valor_anticipo": "60.00",
            "valor_financiado": "90.00",
            "tiene_multiples_clientes": False,
            "tiene_multiples_negociaciones": False,
            "tiene_multiples_estados": True,
            "tiene_multiples_etapas": True,
        }
    ]
