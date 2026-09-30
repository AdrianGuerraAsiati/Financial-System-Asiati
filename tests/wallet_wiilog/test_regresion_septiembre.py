"""Regresión contra el cierre real guardado exclusivamente fuera de Git.

Los Excel y el baseline esperado viven bajo fixtures/, que está ignorado por Git.
El test se salta si el entorno local no tiene el paquete privado completo.
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from app.motores.conciliacion_wallets.wiilog import conciliar_wallet_wiilog
from app.motores.conciliacion_wallets.wiilog.integracion import (
    cargar_parametros_wiilog,
)


RAIZ = Path(__file__).resolve().parents[2]
CARPETA = RAIZ / "fixtures" / "wallet_wiilog" / "2026-09"
BASELINE = CARPETA / "expected_baseline.json"


def _unico(patron: str) -> Path | None:
    archivos = sorted(CARPETA.glob(patron))
    return archivos[0] if len(archivos) == 1 else None


@pytest.fixture(scope="module")
def caso_real():
    ordenes = _unico("ordenes_*.xlsx")
    wallet = _unico("historyWallet_*.xlsx")
    if ordenes is None or wallet is None or not BASELINE.exists():
        pytest.skip(
            "Falta el paquete privado de regresión en fixtures/wallet_wiilog/2026-09."
        )

    esperado = json.loads(BASELINE.read_text(encoding="utf-8"))
    email_principal = esperado.get("wallet_principal_email")
    if not email_principal:
        pytest.fail(
            "expected_baseline.json debe incluir wallet_principal_email para resolver "
            "la configuración real sin versionarla."
        )

    params = cargar_parametros_wiilog(
        wallet_principal_email=email_principal,
    )
    resultado = conciliar_wallet_wiilog(
        pd.read_excel(ordenes),
        pd.read_excel(wallet),
        params,
        esperado["periodo_inicio"],
        esperado["periodo_fin"],
    )
    return resultado, esperado


def test_c0(caso_real):
    resultado, esperado = caso_real
    saldo = resultado.chequeos[0]
    assert saldo.estado == esperado["c0"]["estado"]
    assert saldo.detalle == esperado["c0"]["detalle"]


def test_ordenes_agrupadas(caso_real):
    resultado, esperado = caso_real
    assert len(resultado.ff) == esperado["ordenes_agrupadas"]


def test_ff_por_estado(caso_real):
    resultado, esperado = caso_real
    ff = resultado.ff[resultado.ff.bodega_wiilog]

    assert ff.estado_ff.value_counts().to_dict() == esperado["ff_por_estado"]

    en_juego = ff.groupby("estado_ff").monto_en_juego_c.sum().to_dict()
    for estado, valor in esperado["ff_monto_en_juego_c"].items():
        assert int(en_juego.get(estado, 0)) == int(valor)


def test_ff_no_cobrado_por_bodega(caso_real):
    resultado, esperado = caso_real
    actual = (
        resultado.ff[resultado.ff.estado_ff == "NO_COBRADO"]
        .bodega.value_counts()
        .to_dict()
    )
    assert actual == esperado["ff_no_cobrado_por_bodega"]


def test_ff_fuera_del_reporte(caso_real):
    resultado, esperado = caso_real
    actual = (
        resultado.ff_fuera.groupby("estado_ff")
        .ff_neto_c.agg(["size", "sum"])
    )
    for estado, valores in esperado["ff_fuera"].items():
        assert actual.loc[estado].tolist() == valores


def test_flete(caso_real):
    resultado, esperado = caso_real
    assert (
        resultado.flete.estado_flete.value_counts().to_dict()
        == esperado["flete_por_estado"]
    )
    assert len(resultado.flete_fuera) == esperado["flete_fuera"]


def test_movimientos(caso_real):
    resultado, esperado = caso_real
    movimientos = resultado.movimientos
    assert (
        int((movimientos.estado_categoria != "AUTO").sum())
        == esperado["movimientos"]["por_revisar"]
    )
    assert movimientos.cruce_id.nunique() == esperado["movimientos"]["cruces"]
    assert (
        int((movimientos.concepto == "SIN_CONCEPTO").sum())
        == esperado["movimientos"]["sin_concepto"]
    )
