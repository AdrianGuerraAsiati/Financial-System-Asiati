from dataclasses import dataclass, field


@dataclass(frozen=True)
class ResultadoAceptacion:
    no_pagadas: int
    duplicadas: int
    huerfanas: int


@dataclass(frozen=True)
class ValidacionAceptacion:
    equivalente: bool
    diferencias: dict[str, dict[str, int]] = field(default_factory=dict)


def validar_equivalencia(
    resultado: ResultadoAceptacion,
    esperado: ResultadoAceptacion,
) -> ValidacionAceptacion:
    """Compara una ejecución contra un baseline suministrado explícitamente.

    Los valores de aceptación provenientes de cierres reales no se versionan en
    el código. Deben cargarse desde fixtures privados o desde otra fuente de
    configuración fuera de Git.
    """
    esperados = {
        "no_pagadas": esperado.no_pagadas,
        "duplicadas": esperado.duplicadas,
        "huerfanas": esperado.huerfanas,
    }
    obtenidos = {
        "no_pagadas": resultado.no_pagadas,
        "duplicadas": resultado.duplicadas,
        "huerfanas": resultado.huerfanas,
    }

    diferencias = {
        categoria: {
            "esperado": valor_esperado,
            "obtenido": obtenidos[categoria],
        }
        for categoria, valor_esperado in esperados.items()
        if obtenidos[categoria] != valor_esperado
    }

    return ValidacionAceptacion(
        equivalente=not diferencias,
        diferencias=diferencias,
    )
