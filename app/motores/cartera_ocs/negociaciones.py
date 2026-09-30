from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from app.motores.cartera_ocs.financiacion import (
    DiagnosticoNegociacion,
    diagnosticar_tipo_negociacion,
)
from app.motores.cartera_ocs.importacion import RegistroCarteraEnCamino


@dataclass(frozen=True)
class PatronNegociacionCartera:
    texto: str
    lineas: int
    valor_ddp: Decimal
    diagnostico: DiagnosticoNegociacion


def diagnosticar_negociaciones(
    registros: Iterable[RegistroCarteraEnCamino],
) -> tuple[PatronNegociacionCartera, ...]:
    """Agrupa textos de negociación y hace visibles los fallbacks del parser."""

    acumulado: dict[str, tuple[int, Decimal]] = {}

    for registro in registros:
        texto = str(registro.negociacion or "").strip()
        lineas, valor = acumulado.get(
            texto,
            (0, Decimal("0")),
        )
        acumulado[texto] = (
            lineas + 1,
            valor + registro.valor,
        )

    return tuple(
        PatronNegociacionCartera(
            texto=texto,
            lineas=lineas,
            valor_ddp=valor,
            diagnostico=diagnosticar_tipo_negociacion(texto),
        )
        for texto, (lineas, valor) in sorted(acumulado.items())
    )
