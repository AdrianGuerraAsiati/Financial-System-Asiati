from app.motores.conciliacion_wallets import ConciliacionWallets


def test_wallet_c0_rejects_empty_load() -> None:
    motor = ConciliacionWallets()

    resultado = motor.validar({})

    assert resultado.valido is False
