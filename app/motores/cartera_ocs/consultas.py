from dataclasses import dataclass
from typing import Protocol

from app.motores.cartera_ocs.importacion import RegistroCarteraEnCamino


class OperacionNoEncontradaError(LookupError):
    pass


@dataclass(frozen=True)
class DetalleOperacionCartera:
    oc: str
    lineas: tuple[RegistroCarteraEnCamino, ...]


class FuenteOperacionesCartera(Protocol):
    def listar(
        self,
        *,
        empresa_id: int,
    ) -> tuple[RegistroCarteraEnCamino, ...]: ...


def listar_operaciones(
    fuente: FuenteOperacionesCartera,
    *,
    empresa_id: int,
) -> tuple[RegistroCarteraEnCamino, ...]:
    """Consulta operaciones de Cartera sin conocer la fuente física."""
    return fuente.listar(empresa_id=empresa_id)


def obtener_detalle_operacion(
    fuente: FuenteOperacionesCartera,
    *,
    empresa_id: int,
    oc: str,
) -> DetalleOperacionCartera:
    """Devuelve todas las líneas fuente que pertenecen a una OC."""
    lineas = tuple(
        operacion
        for operacion in fuente.listar(empresa_id=empresa_id)
        if operacion.oc == oc
    )

    if not lineas:
        raise OperacionNoEncontradaError(oc)

    return DetalleOperacionCartera(
        oc=oc,
        lineas=lineas,
    )
