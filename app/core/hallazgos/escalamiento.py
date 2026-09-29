"""Flujo de caso especial (docs/nucleo/ROLES_Y_PERMISOS.md §4)."""

ESTADO_DETECTADO = "detectado"
ESTADO_EN_GESTION = "en_gestion"
ESTADO_ESCALADO = "escalado"
ESTADO_RESUELTO = "resuelto"
ESTADO_CERRADO = "cerrado"

ESTADOS = (
    ESTADO_DETECTADO,
    ESTADO_EN_GESTION,
    ESTADO_ESCALADO,
    ESTADO_RESUELTO,
    ESTADO_CERRADO,
)
ESTADOS_ESCALABLES = (ESTADO_DETECTADO, ESTADO_EN_GESTION)


class TextoObligatorioError(ValueError):
    """Falta la pregunta o la respuesta."""


class EscalamientoInvalidoError(ValueError):
    """El hallazgo no está en un estado que permita la acción."""


def _exigir_texto(texto: str | None, campo: str) -> str:
    limpio = (texto or "").strip()
    if not limpio:
        raise TextoObligatorioError(
            f"Escribe la {campo}: el caso no se puede enviar sin ella."
        )
    return limpio


def transicion_escalar(estado: str, pregunta: str | None) -> str:
    _exigir_texto(pregunta, "pregunta")
    if estado not in ESTADOS_ESCALABLES:
        raise EscalamientoInvalidoError(
            f"Este hallazgo está {estado} y no se puede escalar. "
            "Solo se escalan hallazgos detectados o en gestión."
        )
    return ESTADO_ESCALADO


def transicion_responder(estado: str, respuesta: str | None, *, resolver: bool) -> str:
    _exigir_texto(respuesta, "respuesta")
    if estado != ESTADO_ESCALADO:
        raise EscalamientoInvalidoError(
            f"Este hallazgo está {estado}, no escalado. "
            "Solo se responden casos que están esperando al coordinador."
        )
    return ESTADO_RESUELTO if resolver else ESTADO_EN_GESTION
