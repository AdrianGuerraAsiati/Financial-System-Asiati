"""Lecturas agregadas de Cartera, solo a partir del snapshot autorizado.

Estos importes corresponden a fuentes distintas. No son cobros confirmados,
saldos, exposición neta ni sumandos entre sí.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping


CENTAVO = Decimal("0.01")


def _importe(valor: Any) -> Decimal | None:
    if valor is None:
        return None
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not numero.is_finite():
        return None
    return numero


def _fecha(valor: Any) -> date | None:
    try:
        if not isinstance(valor, str):
            return None
        return date.fromisoformat(valor[:10])
    except ValueError:
        return None


def _formatear(valor: Decimal) -> str:
    return format(valor.quantize(CENTAVO), "f")


def indicadores_cartera(
    filas: Iterable[tuple[str, Mapping[str, Any]]],
    *,
    tipos_validos: set[str],
    hoy: date,
) -> dict[str, object]:
    """Agrupa montos ya normalizados sin interpretar pagos reales.

    Se leen únicamente los tipos de fuente válidos del snapshot de la
    empresa autorizada. El identificador OC se agrupa por texto observado;
    esto no presupone asociación jurídica entre diferentes hojas.
    """
    ocs_operaciones: set[str] = set()
    ocs_proyeccion: set[str] = set()
    proyeccion_total = Decimal("0")
    mora_total = Decimal("0")
    proximos_30 = Decimal("0")
    dias_pasados = Decimal("0")
    por_mes: dict[str, Decimal] = {}
    fechas_proyeccion: set[str] = set()
    con_oc = 0
    registros_proyeccion = 0

    for tipo, data in filas:
        if tipo not in tipos_validos or not data:
            continue
        if tipo == "OPERACIONES":
            oc = str(data.get("oc") or "").strip().upper()
            if oc:
                ocs_operaciones.add(oc)
        elif tipo == "MORA":
            monto = _importe(data.get("monto"))
            if monto is not None:
                mora_total += monto
        elif tipo == "PROYECCION":
            monto = _importe(data.get("monto"))
            fecha = _fecha(data.get("fecha"))
            if monto is None or monto <= 0 or fecha is None:
                continue
            registros_proyeccion += 1
            oc = str(data.get("oc") or "").strip().upper()
            if oc:
                ocs_proyeccion.add(oc)
                con_oc += 1
            proyeccion_total += monto
            if hoy <= fecha <= hoy + timedelta(days=30):
                proximos_30 += monto
            if fecha < hoy:
                dias_pasados += monto
            por_mes[fecha.strftime("%Y-%m")] = (
                por_mes.get(fecha.strftime("%Y-%m"), Decimal("0")) + monto
            )
            fechas_proyeccion.add(fecha.isoformat())

    hoy_mes = date(hoy.year, hoy.month, 1)
    meses: list[dict[str, str]] = []
    for desplazamiento in range(6):
        indice = (hoy_mes.month - 1) + desplazamiento
        anio = hoy_mes.year + (indice // 12)
        mes = indice % 12 + 1
        clave = f"{anio:04d}-{mes:02d}"
        meses.append({"mes": clave, "monto_usd": _formatear(por_mes.get(clave, Decimal("0")))})

    return {
        "ocs_operaciones": len(ocs_operaciones) if "OPERACIONES" in tipos_validos else None,
        "ocs_proyectadas": len(ocs_proyeccion) if "PROYECCION" in tipos_validos else None,
        "monto_proyectado_usd": _formatear(proyeccion_total) if "PROYECCION" in tipos_validos else None,
        "proximos_30_dias_usd": _formatear(proximos_30) if "PROYECCION" in tipos_validos else None,
        "fechas_anteriores_usd": _formatear(dias_pasados) if "PROYECCION" in tipos_validos else None,
        "monto_mora_usd": _formatear(mora_total) if "MORA" in tipos_validos else None,
        "meses_futuros": meses if "PROYECCION" in tipos_validos else [],
        "proyecciones_con_oc": con_oc if "PROYECCION" in tipos_validos else None,
        "registros_proyeccion_utiles": registros_proyeccion if "PROYECCION" in tipos_validos else None,
        "fuentes_validas": sorted(tipos_validos),
        "base": "SNAPSHOT_PERSISTIDO",
    }
