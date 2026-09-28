import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping

from app.motores.cartera_ocs.importacion import parsear_numero_cartera


@dataclass(frozen=True)
class RegistroProyeccionPago:
    cliente: str
    contacto: str
    producto: str
    sku: str
    oc: str
    pais: str
    estado: str
    documento_transporte: str
    dias: float
    valor_oc: float
    comercial: str
    fecha: date
    monto: float
    mes: str


def parsear_fecha_proyeccion(valor: Any) -> date | None:
    """Replica aFechaP() del tablero actual para fechas de proyección."""
    if isinstance(valor, datetime):
        return valor.date()

    if isinstance(valor, date):
        return valor

    texto = str(valor or "").strip()
    if not texto:
        return None

    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", texto)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None

    match = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", texto)
    if match:
        try:
            return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        except ValueError:
            return None

    match = re.match(r"^Date\((\d+),(\d+),(\d+)", texto)
    if match:
        try:
            return date(
                int(match.group(1)),
                int(match.group(2)) + 1,
                int(match.group(3)),
            )
        except ValueError:
            return None

    return None


def normalizar_fila_proyeccion(
    fila: Mapping[str, Any],
) -> RegistroProyeccionPago | None:
    """Normaliza una fila de PROYECCIONES y aplica su filtro actual."""
    fecha = parsear_fecha_proyeccion(fila.get("FECHA DE PAGO ESPERADA"))
    monto = parsear_numero_cartera(fila.get("MONTO ESPERADO"))

    if fecha is None or monto <= 0:
        return None

    contacto = str(fila.get("CLIENTE") or "").strip()
    cliente = str(fila.get("NOMBRE") or "").strip() or contacto or "Sin cliente"
    pais = str(fila.get("PAIS ORIGEN") or "").strip() or "Sin país"
    comercial = str(fila.get("COMERCIAL") or "").strip().upper() or "SIN ASIGNAR"

    return RegistroProyeccionPago(
        cliente=cliente,
        contacto=contacto,
        producto=str(fila.get("DESCRIPCION") or "").strip(),
        sku=str(fila.get("SKU") or "").strip(),
        oc=str(fila.get("NUMERO OC") or "").strip(),
        pais=pais,
        estado=str(fila.get("ESTADO") or "").strip(),
        documento_transporte=str(fila.get("DOCUMENTO DE TRANSPORTE") or "").strip(),
        dias=parsear_numero_cartera(fila.get("DIAS")),
        valor_oc=parsear_numero_cartera(fila.get("VALOR OCI (DDP)")),
        comercial=comercial,
        fecha=fecha,
        monto=monto,
        mes=f"{fecha.year:04d}-{fecha.month:02d}",
    )
