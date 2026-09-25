from app.motores.conciliacion_wallets import ConciliacionWallets


def test_wallet_motor_identity() -> None:
    motor = ConciliacionWallets()

    assert motor.slug == "conciliacion_wallets"
    assert motor.nombre == "Conciliación de Wallets"


def test_wallet_motor_rejects_missing_load() -> None:
    motor = ConciliacionWallets()

    resultado = motor.validar(None)

    assert resultado.valido is False
    assert resultado.errores


def test_wallet_parameter_schema_starts_minimal() -> None:
    motor = ConciliacionWallets()

    schema = motor.esquema_parametros()

    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
