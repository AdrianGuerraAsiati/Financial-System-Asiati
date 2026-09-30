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
class DiagnosticoNegociacion:
    texto_original: str
    terminos: TerminosNegociacion
    porcentajes_detectados: tuple[int, ...]
    dias_detectados: int | None
    porcentaje_interpretable: bool
    plazo_interpretable: bool
    motivos_revision: tuple[str, ...]

    @property
    def requiere_revision(self) -> bool:
        return bool(self.motivos_revision)


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


def diagnosticar_tipo_negociacion(
    tipo_negociacion: str | None,
) -> DiagnosticoNegociacion:
    """Expone cuándo el parser heredado usa un fallback.

    No redefine la regla financiera de MAJO: conserva exactamente sus valores
    por defecto (50 % de saldo y 0 días) y añade evidencia técnica para que una
    negociación ambigua pueda revisarse en lugar de parecer interpretada.
    """

    texto_original = str(tipo_negociacion or "").strip()
    if not texto_original:
        return DiagnosticoNegociacion(
            texto_original="",
            terminos=TerminosNegociacion(
                porcentaje_saldo=Decimal("0.5"),
                dias_plazo=0,
            ),
            porcentajes_detectados=(),
            dias_detectados=None,
            porcentaje_interpretable=False,
            plazo_interpretable=False,
            motivos_revision=("NEGOCIACION_VACIA",),
        )

    texto = _sin_acentos(texto_original.lower())

    porcentajes_texto = re.findall(r"(\d+)%", texto)
    porcentajes = tuple(int(valor) for valor in porcentajes_texto)
    porcentaje_saldo = Decimal("0.5")
    porcentaje_interpretable = False

    if len(porcentajes) >= 2:
        porcentaje_saldo = Decimal(porcentajes[1]) / Decimal("100")
        porcentaje_interpretable = True
    elif len(porcentajes) == 1 and porcentajes[0] < 100:
        porcentaje_saldo = Decimal(100 - porcentajes[0]) / Decimal("100")
        porcentaje_interpretable = True

    dias_plazo = 0
    dias_detectados: int | None = None
    plazo_interpretable = False
    dias_match = re.search(r"pago a (\d+)\s*dia", texto)

    if dias_match:
        dias_plazo = int(dias_match.group(1))
        dias_detectados = dias_plazo
        plazo_interpretable = True
    elif (
        "momento de la entrega" in texto
        or "a la entrega" in texto
    ):
        dias_plazo = 0
        dias_detectados = 0
        plazo_interpretable = True

    motivos: list[str] = []
    if not porcentaje_interpretable:
        motivos.append("PORCENTAJE_NO_INTERPRETABLE")
    if not plazo_interpretable:
        motivos.append("PLAZO_NO_INTERPRETABLE")

    return DiagnosticoNegociacion(
        texto_original=texto_original,
        terminos=TerminosNegociacion(
            porcentaje_saldo=porcentaje_saldo,
            dias_plazo=dias_plazo,
        ),
        porcentajes_detectados=porcentajes,
        dias_detectados=dias_detectados,
        porcentaje_interpretable=porcentaje_interpretable,
        plazo_interpretable=plazo_interpretable,
        motivos_revision=tuple(motivos),
    )


def parsear_tipo_negociacion(tipo_negociacion: str | None) -> TerminosNegociacion:
    """Porta parseNegotiation() de MAJO sin redefinir sus reglas."""
    return diagnosticar_tipo_negociacion(tipo_negociacion).terminos


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
