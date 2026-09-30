from decimal import Decimal

from app.main import app
from app.motores.cartera_ocs.api import obtener_fuente_operaciones
from app.motores.cartera_ocs.importacion import RegistroCarteraEnCamino
from tests.apoyo_auth import cliente_superadmin


class FuenteFake:
    def listar(self, *, empresa_id: int):
        assert empresa_id == 3

        def registro(negociacion: str, valor: str):
            return RegistroCarteraEnCamino(
                cliente="Cliente",
                contacto="",
                producto="",
                sku="SKU",
                oc="OC-1",
                negociacion=negociacion,
                modo_transporte="",
                documento_transporte="",
                estado="",
                anio_oc=2026,
                eta="",
                etapa="EN CAMINO",
                valor=Decimal(valor),
                valor_anticipo=Decimal("0"),
                valor_financiado=Decimal("0"),
                porcentaje_anticipo=Decimal("0"),
            )

        return (
            registro("50% anticipo / 50% pago a 30 días", "100.00"),
            registro("50% anticipo / 50% pago a 30 días", "50.00"),
            registro("Crédito especial", "25.00"),
        )


def test_api_diagnostica_patrones_de_negociacion_sin_cambiar_sus_reglas() -> None:
    app.dependency_overrides[obtener_fuente_operaciones] = lambda: FuenteFake()
    try:
        response = cliente_superadmin().get(
            "/api/v1/cartera/negociaciones/diagnostico?empresa_id=3"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()

    assert body["patrones"] == 2
    assert body["requieren_revision"] == 1

    por_texto = {item["texto"]: item for item in body["items"]}

    interpretable = por_texto["50% anticipo / 50% pago a 30 días"]
    assert interpretable["lineas"] == 2
    assert interpretable["valor_ddp"] == "150.00"
    assert interpretable["porcentaje_saldo"] == "0.5"
    assert interpretable["dias_plazo"] == 30
    assert interpretable["requiere_revision"] is False
    assert interpretable["motivos_revision"] == []

    ambiguo = por_texto["Crédito especial"]
    assert ambiguo["lineas"] == 1
    assert ambiguo["valor_ddp"] == "25.00"
    assert ambiguo["porcentaje_saldo"] == "0.5"
    assert ambiguo["dias_plazo"] == 0
    assert ambiguo["requiere_revision"] is True
    assert ambiguo["motivos_revision"] == [
        "PORCENTAJE_NO_INTERPRETABLE",
        "PLAZO_NO_INTERPRETABLE",
    ]
