import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


COL_CLIENTE = "NOMBRE"
COL_CLIENTE_ALT = "CLIENTE"
COL_PRODUCTO = "DESCRIPCION"
COL_SKU = "SKU"
COL_OC = "NUMERO OC"
COL_NEGOCIACION = "TIPO DE NEGOCIACION"
COL_VALOR = "VALOR OCI (DDP)"
COL_MODO_TRANSPORTE = "MODO TRANSPORTE"
COL_DOCUMENTO_TRANSPORTE = "DOCUMENTO DE TRANSPORTE"
COL_ESTADO = "ESTADO"
COL_ANIO_OC = "AÑO OC"
COL_ETA = "ETA"
COL_PCT_ANTICIPO = "ANTICIPO"
COL_VALOR_ANTICIPO = "VALOR ANTICIPO"
COL_VALOR_FINANCIADO = "VALOR FINANCIADO"
COL_ETAPA = "CARTERA"


@dataclass(frozen=True)
class RegistroCarteraEnCamino:
    cliente: str
    contacto: str
    producto: str
    sku: str
    oc: str
    negociacion: str
    modo_transporte: str
    documento_transporte: str
    estado: str
    anio_oc: Any
    eta: Any
    etapa: str
    valor: Decimal
    valor_anticipo: Decimal
    valor_financiado: Decimal
    porcentaje_anticipo: Decimal


def parsear_numero_cartera(valor: Any) -> Decimal:
    """Replica la interpretación numérica usada por el tablero actual de cartera."""
    if isinstance(valor, bool):
        return Decimal(int(valor))

    if isinstance(valor, (int, float, Decimal)):
        return Decimal(str(valor))

    texto = re.sub(r"[^\d,.\-]", "", str(valor or "")).strip()
    if not texto:
        return Decimal("0")

    tiene_coma = "," in texto
    tiene_punto = "." in texto

    if tiene_coma and tiene_punto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif tiene_coma:
        texto = texto.replace(",", ".")
    elif tiene_punto and re.fullmatch(r"-?\d{1,3}(\.\d{3})+", texto):
        texto = texto.replace(".", "")

    try:
        return Decimal(texto)
    except InvalidOperation:
        return Decimal("0")


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _es_fila_total(*, cliente: str, contacto: str, oc: str, sku: str, producto: str) -> bool:
    valores = (cliente, contacto, oc, sku, producto)
    contiene_total = any(
        re.match(r"^(SUB)?TOTAL(ES)?\b", valor.strip().upper())
        for valor in valores
    )
    return contiene_total and not sku


def normalizar_fila_cartera(
    fila: Mapping[str, Any],
) -> RegistroCarteraEnCamino | None:
    """Normaliza una fila de la hoja FC al contrato interno de Cartera en Camino."""
    cliente = _texto(fila.get(COL_CLIENTE)) or _texto(fila.get(COL_CLIENTE_ALT)) or "Sin cliente"
    contacto = _texto(fila.get(COL_CLIENTE_ALT))
    producto = _texto(fila.get(COL_PRODUCTO))
    sku = _texto(fila.get(COL_SKU))
    oc = _texto(fila.get(COL_OC))

    if _es_fila_total(
        cliente=cliente,
        contacto=contacto,
        oc=oc,
        sku=sku,
        producto=producto,
    ):
        return None

    if not oc and cliente == "Sin cliente":
        return None

    etapa = re.sub(r"^\d+\.\s*", "", _texto(fila.get(COL_ETAPA))) or "Sin clasificar"

    return RegistroCarteraEnCamino(
        cliente=cliente,
        contacto=contacto,
        producto=producto,
        sku=sku,
        oc=oc,
        negociacion=_texto(fila.get(COL_NEGOCIACION)),
        modo_transporte=_texto(fila.get(COL_MODO_TRANSPORTE)),
        documento_transporte=_texto(fila.get(COL_DOCUMENTO_TRANSPORTE)),
        estado=_texto(fila.get(COL_ESTADO)) or "Sin estado",
        anio_oc=fila.get(COL_ANIO_OC, ""),
        eta=fila.get(COL_ETA),
        etapa=etapa,
        valor=parsear_numero_cartera(fila.get(COL_VALOR)),
        valor_anticipo=parsear_numero_cartera(fila.get(COL_VALOR_ANTICIPO)),
        valor_financiado=parsear_numero_cartera(fila.get(COL_VALOR_FINANCIADO)),
        porcentaje_anticipo=parsear_numero_cartera(fila.get(COL_PCT_ANTICIPO)),
    )
