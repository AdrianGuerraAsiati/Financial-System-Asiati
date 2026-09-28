from dataclasses import dataclass
from typing import Any, Mapping

from app.motores.cartera_ocs.importacion import parsear_numero_cartera


@dataclass(frozen=True)
class RegistroCarteraMora:
    cliente: str
    empresa: str
    monto: float
    observacion: str
    estado: str


def normalizar_fila_mora(
    fila: Mapping[str, Any],
) -> RegistroCarteraMora | None:
    """Normaliza una fila de la hoja MORA como lo hace el tablero actual."""
    cliente = str(fila.get("Cliente") or "").strip()
    if not cliente:
        return None

    return RegistroCarteraMora(
        cliente=cliente,
        empresa=str(fila.get("Empresa / Subtítulo") or "").strip(),
        monto=parsear_numero_cartera(fila.get("Monto en mora (USD)")),
        observacion=str(fila.get("Observación más reciente") or "").strip(),
        estado=str(fila.get("CARTERA") or "").strip().upper(),
    )
