from collections.abc import Iterable
from typing import Any, Mapping, Protocol

from app.motores.cartera_ocs.importacion import (
    RegistroCarteraEnCamino,
    normalizar_fila_cartera,
)


class LectorFilasGoogleSheets(Protocol):
    def leer_filas(
        self,
        *,
        empresa_id: int,
    ) -> Iterable[Mapping[str, Any]]: ...


class FuenteOperacionesGoogleSheets:
    """Adapta filas provenientes de Google Sheets al contrato de Cartera."""

    def __init__(self, lector: LectorFilasGoogleSheets) -> None:
        self.lector = lector

    def listar(
        self,
        *,
        empresa_id: int,
    ) -> tuple[RegistroCarteraEnCamino, ...]:
        operaciones: list[RegistroCarteraEnCamino] = []

        for fila in self.lector.leer_filas(empresa_id=empresa_id):
            registro = normalizar_fila_cartera(fila)
            if registro is not None:
                operaciones.append(registro)

        return tuple(operaciones)
