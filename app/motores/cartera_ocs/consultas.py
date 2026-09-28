from typing import Protocol

from app.motores.cartera_ocs.importacion import RegistroCarteraEnCamino


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
