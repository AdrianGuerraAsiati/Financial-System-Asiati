from app.motores.conciliacion_wallets.acceptance import (
    ResultadoAceptacion,
    validar_equivalencia,
)


BASELINE_SINTETICO = ResultadoAceptacion(
    no_pagadas=12,
    duplicadas=3,
    huerfanas=4,
)


def test_wallet_acceptance_matches_supplied_baseline() -> None:
    validacion = validar_equivalencia(
        ResultadoAceptacion(no_pagadas=12, duplicadas=3, huerfanas=4),
        BASELINE_SINTETICO,
    )

    assert validacion.equivalente is True
    assert validacion.diferencias == {}


def test_wallet_acceptance_reports_each_difference() -> None:
    validacion = validar_equivalencia(
        ResultadoAceptacion(no_pagadas=11, duplicadas=5, huerfanas=2),
        BASELINE_SINTETICO,
    )

    assert validacion.equivalente is False
    assert validacion.diferencias == {
        "no_pagadas": {"esperado": 12, "obtenido": 11},
        "duplicadas": {"esperado": 3, "obtenido": 5},
        "huerfanas": {"esperado": 4, "obtenido": 2},
    }
