from dataclasses import dataclass
from decimal import Decimal

from app.core.cargas import calcular_hash_contenido
from app.motores.cartera_ocs.financiacion import CondicionPago


ESTADO_AUDITORIA_PENDIENTE = "PENDIENTE"
ESTADO_AUDITORIA_PENDIENTE_ASOCIACION = "PENDIENTE_ASOCIACION"
ESTADOS_AUDITORIA_PENDIENTES = (
    ESTADO_AUDITORIA_PENDIENTE,
    ESTADO_AUDITORIA_PENDIENTE_ASOCIACION,
)


@dataclass(frozen=True)
class ComprobantePago:
    oc: str
    cliente: str | None
    pais: str | None
    comercial: str | None
    monto_esperado: Decimal | None
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


def radicar_comprobante_simple(
    *, oc: str, nombre_archivo: str, contenido: bytes
) -> ComprobantePago:
    """Radica el soporte, sin atribuir una condición financiera no verificada.

    El comprobante queda en la bandeja de revisión; no se considera aplicado
    a cartera ni se calcula/infiera un importe desde otras fuentes.
    """
    return ComprobantePago(
        oc=oc.strip(),
        cliente=None,
        pais=None,
        comercial=None,
        monto_esperado=None,
        nombre_archivo=nombre_archivo,
        contenido_hash=calcular_hash_contenido(contenido),
        estado_auditoria=ESTADO_AUDITORIA_PENDIENTE_ASOCIACION,
    )
