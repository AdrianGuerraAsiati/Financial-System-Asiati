"""Controles de corte sin inferir decisiones financieras."""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock
import pytest

from app.motores.conciliacion_wallets.corte_operativo import validar_corte, clasificar_movimiento

def _periodo():
    return Mock(fecha_inicio=date(2026, 9, 1), fecha_fin=date(2026, 9, 30))

def test_bogota_es_valida_solo_si_se_declara():
    utc = validar_corte("America/Bogota", datetime(2026, 9, 30, 23, 59), _periodo())
    assert utc == datetime(2026, 10, 1, 4, 59, tzinfo=timezone.utc)

def test_sin_zona_y_fuera_de_periodo_no_pasan():
    with pytest.raises(ValueError, match="America/Bogota"):
        validar_corte("Zona/Ficticia", datetime(2026, 9, 30, 12), _periodo())
    with pytest.raises(ValueError, match="período"):
        validar_corte("America/Bogota", datetime(2026, 10, 1, 0), _periodo())

def test_rechaza_otra_zona_incluso_si_es_iana_valida():
    with pytest.raises(ValueError, match="America/Bogota"):
        validar_corte("America/New_York", datetime(2026, 9, 30, 12), _periodo())
    with pytest.raises(ValueError, match="America/Bogota"):
        validar_corte("UTC", datetime(2026, 9, 30, 12), _periodo())

def test_clasificacion_temporal_incluye_limite():
    corte = datetime(2026, 10, 1, 0, tzinfo=timezone.utc)
    antes = corte - timedelta(minutes=1)
    despues = corte + timedelta(minutes=1)
    assert clasificar_movimiento(instante_movimiento=antes, instante_recepcion=antes, corte_utc=corte) == "EN_CORTE"
    assert clasificar_movimiento(instante_movimiento=antes, instante_recepcion=despues, corte_utc=corte) == "TARDIO_DEL_PERIODO"
    assert clasificar_movimiento(instante_movimiento=despues, instante_recepcion=despues, corte_utc=corte) == "POST_CORTE"

def test_rechaza_instante_naive():
    with pytest.raises(ValueError, match="zona horaria"):
        clasificar_movimiento(instante_movimiento=datetime(2026, 9, 1),
                             instante_recepcion=datetime.now(timezone.utc),
                             corte_utc=datetime.now(timezone.utc))
