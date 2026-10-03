import re
from datetime import date, datetime
from typing import Any


def parsear_fecha_cartera(valor: Any) -> date | None:
    """Centraliza la interpretación de fechas heredada del tablero de Cartera.

    Acepta los formatos observados en Google Sheets / gviz sin inferir formatos
    adicionales: ISO, día/mes/año y Date(año, mes_cero, día).
    """
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
            return date(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            )
        except ValueError:
            return None

    match = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", texto)
    if match:
        try:
            return date(
                int(match.group(3)),
                int(match.group(2)),
                int(match.group(1)),
            )
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
