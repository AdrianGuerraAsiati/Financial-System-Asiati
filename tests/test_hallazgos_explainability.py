from app.core.hallazgos.creation import registrar_hallazgo_motor


class SpySession:
    def __init__(self) -> None:
        self.added = []

    def add(self, entity) -> None:
        self.added.append(entity)


def test_motor_finding_keeps_explanation_metadata() -> None:
    session = SpySession()

    hallazgo = registrar_hallazgo_motor(
        session,
        periodo_id=10,
        motor_slug="conciliacion_wallets",
        codigo_regla="wallet_pago_no_encontrado",
        descripcion="No se encontró un pago conciliable para la orden.",
        evidencia={
            "orden_id": "OC-123",
            "valor": 2500000,
            "matches": 0,
        },
        critico=True,
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
    assert hallazgo.resuelto is False
