from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from typing import Any, Mapping, Protocol

from app.motores.cartera_ocs.fechas import parsear_fecha_cartera
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
    dias: Decimal
    valor_oc: Decimal
    comercial: str
    fecha: date
    monto: Decimal
    mes: str


def parsear_fecha_proyeccion(valor: Any) -> date | None:
    """Mantiene el nombre público del parser legado usando el parser compartido."""
    return parsear_fecha_cartera(valor)


def normalizar_fila_proyeccion(
    fila: Mapping[str, Any],
) -> RegistroProyeccionPago | None:
    """Normaliza una fila de PROYECCIONES y aplica su filtro actual."""
    fecha = parsear_fecha_proyeccion(fila.get("FECHA DE PAGO ESPERADA"))
    monto = parsear_numero_cartera(fila.get("MONTO ESPERADO"))

    if fecha is None or monto <= Decimal("0"):
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



class FuenteProyeccionCartera(Protocol):
    def listar(
        self,
        *,
        empresa_id: int,
    ) -> tuple[RegistroProyeccionPago, ...]: ...


def listar_proyeccion(
    fuente: FuenteProyeccionCartera,
    *,
    empresa_id: int,
) -> tuple[RegistroProyeccionPago, ...]:
    return fuente.listar(empresa_id=empresa_id)
