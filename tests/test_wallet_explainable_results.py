from app.core.motor import Resultado
from app.motores.conciliacion_wallets.hallazgos import registrar_resultado


class SpySession:
    def __init__(self) -> None:
        self.added = []

    def add(self, entity) -> None:
        self.added.append(entity)


def test_wallet_result_is_translated_to_explainable_finding() -> None:
    session = SpySession()
    resultado = Resultado(
        codigo="wallet_pago_no_encontrado",
        estado="requiere_revision",
        datos={
            "orden_id": "OC-123",
            "valor": 2500000,
            "matches": 0,
        },
        descripcion="No se encontró un pago conciliable para la orden.",
        critico=True,
    )

    hallazgo = registrar_resultado(
        session,
        periodo_id=10,
        resultado=resultado,
    )

    assert hallazgo in session.added
    assert hallazgo.periodo_id == 10
    assert hallazgo.motor_slug == "conciliacion_wallets"
    assert hallazgo.codigo_regla == "wallet_pago_no_encontrado"
    assert hallazgo.descripcion == "No se encontró un pago conciliable para la orden."
    assert hallazgo.evidencia == {
        "orden_id": "OC-123",
        "valor": 2500000,
        "matches": 0,
    }
    assert hallazgo.critico is True
