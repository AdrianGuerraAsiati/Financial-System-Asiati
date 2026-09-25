from app.motores.conciliacion_wallets.acceptance import (
    ResultadoAceptacion,
    validar_equivalencia,
)


def test_wallet_acceptance_matches_known_validated_baseline() -> None:
    resultado = ResultadoAceptacion(
        no_pagadas=1555,
        duplicadas=28,
        huerfanas=80,
    )

    validacion = validar_equivalencia(resultado)

    assert validacion.equivalente is True
    assert validacion.diferencias == {}


def test_wallet_acceptance_reports_each_difference() -> None:
    resultado = ResultadoAceptacion(
        no_pagadas=1554,
        duplicadas=30,
        huerfanas=79,
    )

    validacion = validar_equivalencia(resultado)

    assert validacion.equivalente is False
    assert validacion.diferencias == {
        "no_pagadas": {"esperado": 1555, "obtenido": 1554},
        "duplicadas": {"esperado": 28, "obtenido": 30},
        "huerfanas": {"esperado": 80, "obtenido": 79},
    }
