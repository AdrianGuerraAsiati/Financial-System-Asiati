"""Gate local para regresiones de Wallets con evidencia privada.

No ejecutar en CI público: los fallos de una regresión real pueden mostrar
valores operativos en la salida de pytest. No crea ni modifica baselines.
"""
from __future__ import annotations

import sys

import pytest


PRUEBAS_PRIVADAS = (
    "tests/wallet_wiilog/test_regresion_septiembre.py",
    "tests/wallet_tiendas/test_regresion_tiendas_septiembre.py",
)


class BloqueadorOmisiones:
    def __init__(self) -> None:
        self.omitidas = 0

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.skipped:
            self.omitidas += 1


def ejecutar() -> int:
    auditor = BloqueadorOmisiones()
    estado = pytest.main(["-q", "-ra", *PRUEBAS_PRIVADAS], plugins=[auditor])
    if auditor.omitidas:
        print(
            f"REGRESION PRIVADA NO ACEPTADA: {auditor.omitidas} pruebas omitidas. "
            "Verificar fixtures y configuracion runtime privada.",
            file=sys.stderr,
        )
        return 2
    if estado != pytest.ExitCode.OK:
        print(
            "REGRESION PRIVADA NO ACEPTADA: pytest no termino correctamente.",
            file=sys.stderr,
        )
    else:
        print(
            "SUITES PRIVADAS PASS. Esto no certifica las cinco wallets: "
            "Recompra Menpros no tiene regresion dedicada en estas suites."
        )
    return int(estado)


if __name__ == "__main__":
    raise SystemExit(ejecutar())
