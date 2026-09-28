"""Normalización de texto, montos y fechas. Python puro, sin base de datos."""
from __future__ import annotations

import re
import unicodedata
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd


def texto(valor: object) -> str:
    """Mayúsculas, sin tildes, sin tabulaciones, espacios colapsados."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    s = unicodedata.normalize("NFKD", str(valor))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s).strip().upper()
    return s


def centavos(valor: object) -> int:
    """Convierte un monto del archivo a centavos enteros. Nunca se opera dinero en float."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return 0
    d = Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(d * 100)


def pesos(cents: int) -> Decimal:
    return (Decimal(int(cents)) / Decimal(100)).quantize(Decimal("0.01"))


def orden_id(valor: object) -> str | None:
    """Los IDs llegan como float desde Excel (89934467.0). Se guardan como texto sin decimales."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    s = str(valor).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s or None


def fecha(serie: pd.Series, formato: str) -> pd.Series:
    return pd.to_datetime(serie, format=formato, errors="coerce")
