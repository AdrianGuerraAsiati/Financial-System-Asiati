import pytest

from app.core.hallazgos.escalamiento import (
    ESTADO_DETECTADO,
    ESTADO_EN_GESTION,
    ESTADO_ESCALADO,
    ESTADO_RESUELTO,
    ESTADOS,
    EscalamientoInvalidoError,
    TextoObligatorioError,
    transicion_escalar,
    transicion_responder,
)


def test_states_follow_the_special_case_flow() -> None:
    assert ESTADOS == ("detectado", "en_gestion", "escalado", "resuelto", "cerrado")


@pytest.mark.parametrize("estado", [ESTADO_DETECTADO, ESTADO_EN_GESTION])
def test_open_finding_can_be_escalated_with_a_question(estado: str) -> None:
    assert transicion_escalar(estado, "¿Se cobra este flete?") == ESTADO_ESCALADO


@pytest.mark.parametrize("pregunta", ["", "   ", None])
def test_escalating_without_a_question_is_rejected(pregunta: str | None) -> None:
    with pytest.raises(TextoObligatorioError, match="pregunta"):
        transicion_escalar(ESTADO_DETECTADO, pregunta)


@pytest.mark.parametrize("estado", [ESTADO_ESCALADO, ESTADO_RESUELTO, "cerrado"])
def test_only_open_findings_can_be_escalated(estado: str) -> None:
    with pytest.raises(EscalamientoInvalidoError):
        transicion_escalar(estado, "pregunta")


def test_answer_returns_case_to_reconciler() -> None:
    assert (
        transicion_responder(ESTADO_ESCALADO, "Sí, se cobra", resolver=False)
        == ESTADO_EN_GESTION
    )


def test_answer_can_resolve_the_case_directly() -> None:
    assert (
        transicion_responder(ESTADO_ESCALADO, "Se acepta la diferencia", resolver=True)
        == ESTADO_RESUELTO
    )


def test_answer_requires_text() -> None:
    with pytest.raises(TextoObligatorioError, match="respuesta"):
        transicion_responder(ESTADO_ESCALADO, " ", resolver=True)


def test_only_escalated_findings_can_be_answered() -> None:
    with pytest.raises(EscalamientoInvalidoError):
        transicion_responder(ESTADO_DETECTADO, "respuesta", resolver=False)
