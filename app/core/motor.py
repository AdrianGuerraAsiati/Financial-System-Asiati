from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ResultadoValidacion:
    valido: bool
    errores: tuple[str, ...] = ()


@dataclass(frozen=True)
class Resultado:
    codigo: str
    estado: str
    datos: dict[str, Any]


class Motor(Protocol):
    """
    Contrato provisional.

    No debe considerarse definitivo hasta construir el segundo motor.
    El objetivo es evitar abstraer el core antes de tener evidencia real
    de qué capacidades son comunes.
    """

    slug: str
    nombre: str

    def esquema_parametros(self) -> dict[str, Any]:
        ...

    def validar(self, carga: Any) -> ResultadoValidacion:
        ...

    def ejecutar(
        self,
        periodo: str,
        params: dict[str, Any],
    ) -> list[Resultado]:
        ...
