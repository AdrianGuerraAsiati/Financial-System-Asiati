"""Equivalencias descriptivas de PAGOS; no aplican abonos a obligaciones.

Contrato observado en CARTERA V1: PAGOS!K:O y TRM_Historica!A:E.
Usar tasa de la fecha del pago o la ultima anterior disponible.
No hay escrituras ni una conciliacion pago-OC en este modulo.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable


@dataclass(frozen=True)
class TasaHistoricaPago:
    fecha: date
    cop_por_usd: Decimal
    clp_por_usd: Decimal


@dataclass(frozen=True)
class EquivalenciaPago:
    fecha_pago: date
    fecha_tasa: date
    divisa: str
    monto_original: Decimal
    cop_referencia: Decimal
    usd_referencia: Decimal


def seleccionar_tasa_pago(
    fecha_pago: date, historico: Iterable[TasaHistoricaPago]
) -> TasaHistoricaPago:
    """Busca coincidencia exacta o la ultima tasa anterior (XLOOKUP -1)."""
    tasas: dict[date, TasaHistoricaPago] = {}
    for tasa in historico:
        if tasa.fecha in tasas and tasas[tasa.fecha] != tasa:
            raise ValueError("Existen tasas historicas contradictorias para una fecha.")
        tasas[tasa.fecha] = tasa

    elegibles = [fecha for fecha in tasas if fecha <= fecha_pago]
    if not elegibles:
        raise ValueError("No existe tasa historica en o antes del pago.")
    return tasas[max(elegibles)]


def convertir_pago_referencia(
    *,
    fecha_pago: date,
    divisa: str,
    monto: Decimal,
    historico: Iterable[TasaHistoricaPago],
) -> EquivalenciaPago:
    """Replica conversiones de PAGOS!N:O sin redondear ni sumar obligaciones.

    COP REF: USD*TRM, COP, (CLP/USDCLP)*TRM.
    USD REF: USD, COP/TRM, CLP/USDCLP.
    Los montos conservan precision Decimal hasta la presentacion.
    """
    if not isinstance(monto, Decimal) or not monto.is_finite():
        raise ValueError("El monto debe ser un Decimal finito.")

    moneda = divisa.strip().upper()
    if moneda not in {"COP", "USD", "CLP"}:
        raise ValueError(f"Divisa no soportada: {moneda or '(vacia)'}.")

    tasa = seleccionar_tasa_pago(fecha_pago, historico)
    if not tasa.cop_por_usd.is_finite() or tasa.cop_por_usd <= 0:
        raise ValueError("TRM USD/COP invalida.")
    if moneda == "CLP" and (
        not tasa.clp_por_usd.is_finite() or tasa.clp_por_usd <= 0
    ):
        raise ValueError("Tasa USD/CLP invalida.")

    if moneda == "USD":
        usd = monto
        cop = monto * tasa.cop_por_usd
    elif moneda == "COP":
        cop = monto
        usd = monto / tasa.cop_por_usd
    else:
        usd = monto / tasa.clp_por_usd
        cop = usd * tasa.cop_por_usd

    return EquivalenciaPago(
        fecha_pago=fecha_pago,
        fecha_tasa=tasa.fecha,
        divisa=moneda,
        monto_original=monto,
        cop_referencia=cop,
        usd_referencia=usd,
    )
