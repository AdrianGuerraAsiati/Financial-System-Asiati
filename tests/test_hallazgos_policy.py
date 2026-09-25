from app.core.hallazgos import Hallazgo
from app.core.hallazgos.service import hay_criticos_abiertos


def test_open_critical_finding_is_detected() -> None:
    hallazgos = [
        Hallazgo(periodo_id=1, critico=True, resuelto=False),
        Hallazgo(periodo_id=1, critico=False, resuelto=False),
    ]

    assert hay_criticos_abiertos(hallazgos) is True


def test_resolved_critical_finding_does_not_block() -> None:
    hallazgos = [
        Hallazgo(periodo_id=1, critico=True, resuelto=True),
        Hallazgo(periodo_id=1, critico=False, resuelto=False),
    ]

    assert hay_criticos_abiertos(hallazgos) is False


def test_no_findings_means_no_open_critical_findings() -> None:
    assert hay_criticos_abiertos([]) is False
