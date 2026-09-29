from dataclasses import dataclass
from decimal import Decimal

from app.core.cargas import calcular_hash_contenido
from app.motores.cartera_ocs.financiacion import CondicionPago


ESTADO_AUDITORIA_PENDIENTE = "PENDIENTE"


@dataclass(frozen=True)
class ComprobantePago:
    oc: str
    cliente: str
    pais: str
    comercial: str
    monto_esperado: Decimal
    nombre_archivo: str
    contenido_hash: str
    estado_auditoria: str


def radicar_comprobante(
    *,
    condicion: CondicionPago,
    nombre_archivo: str,
    contenido: bytes,
) -> ComprobantePago:
    """Radica un comprobante contra una condición de pago y lo deja pendiente."""
    return ComprobantePago(
        oc=condicion.oc,
        cliente=condicion.cliente,
        pais=condicion.pais,
        comercial=condicion.comercial,
        monto_esperado=condicion.monto_original,
        nombre_archivo=nombre_archivo,
        contenido_hash=calcular_hash_contenido(contenido),
        estado_auditoria=ESTADO_AUDITORIA_PENDIENTE,
    )
