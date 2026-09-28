"""Test de regresión con los archivos reales de septiembre 2026.

Los archivos viven en fixtures/ y NO se suben a git. Si no están, el test se salta.
Las cifras esperadas están documentadas en docs/motores/conciliacion_wallets/WALLET_WIILOG.md §7.
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from app.motores.conciliacion_wallets.wiilog import conciliar_wallet_wiilog

RAIZ = Path(__file__).resolve().parents[2]
ORDENES = RAIZ / "fixtures/wallet_wiilog/2026-09/ordenes_sept_20260928_144134.xlsx"
WALLET = RAIZ / "fixtures/wallet_wiilog/2026-09/historyWallet_20260928_142641.xlsx"

pytestmark = [
    pytest.mark.fixtures_reales,
    pytest.mark.skipif(not (ORDENES.exists() and WALLET.exists()), reason="Faltan los archivos reales de septiembre en fixtures/"),
]


@pytest.fixture(scope="module")
def resultado():
    params = json.loads((RAIZ / "docs/motores/conciliacion_wallets/parametros_wallet_wiilog.json").read_text(encoding="utf-8"))
    return conciliar_wallet_wiilog(pd.read_excel(ORDENES), pd.read_excel(WALLET), params, "2026-09-01", "2026-09-30")


def test_c0(resultado):
    saldo = resultado.chequeos[0]
    assert saldo.estado == "EN_ORDEN"
    assert saldo.detalle == {
        "saldo_inicial": "3000.72",
        "entradas": "86853298.80",
        "salidas": "51107944.97",
        "saldo_final": "35748354.55",
        "quiebres": 0,
    }


def test_ordenes_agrupadas(resultado):
    assert len(resultado.ff) == 23093


def test_ff_por_estado(resultado):
    ff = resultado.ff[resultado.ff.bodega_wiilog]
    assert ff.estado_ff.value_counts().to_dict() == {
        "COBRADO": 17634,
        "NO_APLICA": 4276,
        "NO_COBRADO": 685,
        "DUPLICADO": 98,
        "EN_VENTANA": 80,
        "PENDIENTE_CIERRE": 74,
        "REVERSADO": 25,
        "DIFERENCIA_TARIFA": 12,
    }
    en_juego = ff.groupby("estado_ff").monto_en_juego_c.sum()
    assert en_juego["NO_COBRADO"] == 171_250_000
    assert en_juego["DUPLICADO"] == 24_500_000
    assert en_juego["DIFERENCIA_TARIFA"] == 3_000_000


def test_ff_no_cobrado_por_bodega(resultado):
    nc = resultado.ff[resultado.ff.estado_ff == "NO_COBRADO"].bodega.value_counts().to_dict()
    assert nc == {"WIILOG BUCARAMANGA": 677, "WIILOG BOGOTA": 7, "WIILOG BOGOTA 3.0": 1}


def test_ff_fuera_del_reporte(resultado):
    fuera = resultado.ff_fuera.groupby("estado_ff").ff_neto_c.agg(["size", "sum"])
    assert fuera.loc["FUERA_DEL_REPORTE"].tolist() == [1333, 346_124_987]
    assert fuera.loc["FUERA_MARCA_BLANCA"].tolist() == [1461, 365_249_994]


def test_flete(resultado):
    assert resultado.flete.estado_flete.value_counts().to_dict() == {
        "COBRADO": 8991,
        "NO_APLICA": 6600,
        "SIN_VERIFICAR": 4268,
        "PENDIENTE_CIERRE": 3234,
    }
    assert len(resultado.flete_fuera) == 4049


def test_movimientos(resultado):
    m = resultado.movimientos
    assert (m.estado_categoria != "AUTO").sum() == 10
    assert m.cruce_id.nunique() == 18
    assert (m.concepto == "SIN_CONCEPTO").sum() == 0
