from __future__ import annotations

from datetime import date, datetime


def parsear_fecha_fuente(valor: str) -> date | None:
    texto = str(valor or "").strip()
    if not texto:
        return None

    formatos = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
    )
    for formato in formatos:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None
