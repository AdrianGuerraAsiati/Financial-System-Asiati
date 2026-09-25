from dataclasses import dataclass, field


BASELINE_NO_PAGADAS = 1555
BASELINE_DUPLICADAS = 28
BASELINE_HUERFANAS = 80


@dataclass(frozen=True)
class ResultadoAceptacion:
    no_pagadas: int
    duplicadas: int
    huerfanas: int


@dataclass(frozen=True)
class ValidacionAceptacion:
    equivalente: bool
    diferencias: dict[str, dict[str, int]] = field(default_factory=dict)


def validar_equivalencia(resultado: ResultadoAceptacion) -> ValidacionAceptacion:
    """Compara la ejecución contra el caso real validado de Wallets."""
    esperados = {
        "no_pagadas": BASELINE_NO_PAGADAS,
        "duplicadas": BASELINE_DUPLICADAS,
        "huerfanas": BASELINE_HUERFANAS,
    }
    obtenidos = {
        "no_pagadas": resultado.no_pagadas,
        "duplicadas": resultado.duplicadas,
        "huerfanas": resultado.huerfanas,
    }

    diferencias = {
        categoria: {
            "esperado": esperado,
            "obtenido": obtenidos[categoria],
        }
        for categoria, esperado in esperados.items()
        if obtenidos[categoria] != esperado
    }

    return ValidacionAceptacion(
        equivalente=not diferencias,
        diferencias=diferencias,
    )
