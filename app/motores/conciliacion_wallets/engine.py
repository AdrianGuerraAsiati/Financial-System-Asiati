from typing import Any

from app.core.motor import Resultado, ResultadoValidacion


class ConciliacionWallets:
    slug = "conciliacion_wallets"
    nombre = "Conciliación de Wallets"

    def esquema_parametros(self) -> dict[str, Any]:
        # Se completará con los catálogos y reglas levantados del proceso real.
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }

    def validar(self, carga: Any) -> ResultadoValidacion:
        # C0 mínimo: una carga ausente o vacía no puede avanzar al motor.
        # El contrato real de archivos se definirá con las fuentes operativas.
        if carga is None or carga == {}:
            return ResultadoValidacion(
                valido=False,
                errores=("La carga es obligatoria.",),
            )
        return ResultadoValidacion(valido=True)

    def ejecutar(
        self,
        periodo: str,
        params: dict[str, Any],
    ) -> list[Resultado]:
        raise NotImplementedError(
            "Pendiente implementar las reglas reales de conciliación de wallets."
        )
