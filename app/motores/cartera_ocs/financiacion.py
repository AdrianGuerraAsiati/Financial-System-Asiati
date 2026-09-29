import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from datetime import date, timedelta


@dataclass(frozen=True)
class TerminosNegociacion:
    porcentaje_saldo: Decimal
    dias_plazo: int


@dataclass(frozen=True)
class OperacionFinanciada:
    oc: str
    cliente: str
    pais: str
    valor_ddp: Decimal
    tipo_negociacion: str
    fecha_entrega: date
    comercial: str


@dataclass(frozen=True)
class CondicionPago:
    oc: str
    cliente: str
    pais: str
    comercial: str
    porcentaje_saldo: Decimal
    dias_plazo: int
    fecha_pago_esperada: date
    monto_original: Decimal


def _sin_acentos(texto: str) -> str:
    normalizado = unicodedata.normalize("NFD", texto)
    return "".join(
        caracter
        for caracter in normalizado
        if unicodedata.category(caracter) != "Mn"
    )


def parsear_tipo_negociacion(tipo_negociacion: str | None) -> TerminosNegociacion:
    """Porta parseNegotiation() de MAJO sin redefinir sus reglas."""
    if not tipo_negociacion:
        return TerminosNegociacion(
            porcentaje_saldo=Decimal("0.5"),
            dias_plazo=0,
        )

    texto = _sin_acentos(str(tipo_negociacion).lower())

    porcentajes = re.findall(r"(\d+)%", texto)
    porcentaje_saldo = Decimal("0.5")

    if len(porcentajes) >= 2:
        porcentaje_saldo = Decimal(porcentajes[1]) / Decimal("100")
    elif len(porcentajes) == 1:
        valor = int(porcentajes[0])
        if valor < 100:
            porcentaje_saldo = Decimal(100 - valor) / Decimal("100")

    dias_plazo = 0
    dias_match = re.search(r"pago a (\d+)\s*dia", texto)

    if dias_match:
        dias_plazo = int(dias_match.group(1))
    elif (
        "momento de la entrega" in texto
        or "a la entrega" in texto
    ):
        dias_plazo = 0

    return TerminosNegociacion(
        porcentaje_saldo=porcentaje_saldo,
        dias_plazo=dias_plazo,
    )


def generar_condicion_pago(
    operacion: OperacionFinanciada,
) -> CondicionPago:
    """Genera la condición de pago que MAJO deriva de una operación entregada."""
    terminos = parsear_tipo_negociacion(operacion.tipo_negociacion)

    return CondicionPago(
        oc=operacion.oc,
        cliente=operacion.cliente,
        pais=operacion.pais,
        comercial=operacion.comercial,
        porcentaje_saldo=terminos.porcentaje_saldo,
        dias_plazo=terminos.dias_plazo,
        fecha_pago_esperada=(
            operacion.fecha_entrega
            + timedelta(days=terminos.dias_plazo)
        ),
        monto_original=(
            operacion.valor_ddp
            * terminos.porcentaje_saldo
        ),
    )
