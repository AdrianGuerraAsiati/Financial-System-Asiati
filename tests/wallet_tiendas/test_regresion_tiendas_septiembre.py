"""Regresión con los archivos reales de septiembre 2026 (Menpros, Proveeduría ASIATI, pagos@asiati).

Los archivos viven en fixtures/ y NO se suben a git. Si no están, el test se salta.
Las cifras esperadas están en docs/motores/conciliacion_wallets/WALLETS_TIENDAS_Y_PAGOS.md §6.
"""
import json
import os
from pathlib import Path

import pandas as pd
import pytest

from app.motores.conciliacion_wallets.pagos import conciliar_wallet_pagos
from app.motores.conciliacion_wallets.plataforma.hallazgos import hallazgos_tienda
from app.motores.conciliacion_wallets.tiendas import conciliar_wallet_tienda
from app.motores.conciliacion_wallets.wiilog.integracion import resolver_identificador_wallet

RAIZ = Path(__file__).resolve().parents[2]
DOCS = RAIZ / "docs/motores/conciliacion_wallets"
FIX = RAIZ / "fixtures/wallet_tiendas/2026-09"
ORDENES = RAIZ / "fixtures/wallet_wiilog/2026-09/ordenes_sept_20260928_144134.xlsx"
MENPROS = FIX / "wallet_menpros_20260929.xlsx"
PROVEEDURIA = FIX / "wallet_proveeduria_asiati_20260929.xlsx"
PAGOS = FIX / "wallet_pagos_asiati_20260929.xlsx"
WIILOG_RUNTIME_EMAIL = os.getenv("WIILOG_WALLET_PRINCIPAL_EMAIL", "").strip()

pytestmark = [
    pytest.mark.fixtures_reales,
    pytest.mark.skipif(not all(p.exists() for p in (ORDENES, MENPROS, PROVEEDURIA, PAGOS)),
                       reason="Faltan los archivos reales de septiembre en fixtures/"),
    pytest.mark.skipif(not WIILOG_RUNTIME_EMAIL,
                       reason="Falta WIILOG_WALLET_PRINCIPAL_EMAIL para resolver el baseline privado"),
]


def _json(nombre):
    return json.loads((DOCS / nombre).read_text(encoding="utf-8"))


def _json_runtime(nombre):
    return resolver_identificador_wallet(
        _json(nombre),
        wallet_principal_email=WIILOG_RUNTIME_EMAIL,
    )


@pytest.fixture(scope="module")
def entorno():
    params = _json_runtime("parametros_wallet_tienda.json")
    return {
        "params": params,
        "catalogo": _json_runtime("catalogo_conceptos_wallets.json"),
        "tarifas": _json("parametros_wallet_wiilog.json")["fulfillment"]["tarifas_por_bodega"],
        "ordenes": pd.read_excel(ORDENES),
        "tiendas": {t["nombre"]: t for t in params["tiendas"]},
    }


def _correr(e, archivo, nombre):
    return conciliar_wallet_tienda(e["ordenes"], pd.read_excel(archivo), e["params"], e["catalogo"], e["tiendas"][nombre],
                                   "2026-09-01", "2026-09-30", e["tarifas"], corte_ordenes="2026-09-28 14:41")


@pytest.fixture(scope="module")
def menpros(entorno):
    return _correr(entorno, MENPROS, "Menpros")


@pytest.fixture(scope="module")
def proveeduria(entorno):
    return _correr(entorno, PROVEEDURIA, "Proveeduría ASIATI")


def test_menpros_c0(menpros):
    assert menpros.chequeos[0].detalle == {
        "saldo_inicial": "33327591.35", "entradas": "349528529.28", "salidas": "309063745.47",
        "saldo_final": "73792375.17", "quiebres": 0}
    assert (menpros.movimientos.concepto == "SIN_CONCEPTO").sum() == 0


def test_menpros_ganancia(menpros):
    assert menpros.ganancia.estado.value_counts().to_dict() == {
        "PAGADA": 4329, "NO_APLICA": 3595, "PAGADA_SIN_VALIDAR": 119, "PAGO_POSTERIOR_AL_REPORTE": 113}


def test_menpros_sin_recaudo(menpros):
    s = menpros.sin_recaudo
    assert s.estado_cobro.value_counts().to_dict() == {"COBRO_CORRECTO": 444}
    assert s.estado_reembolso.value_counts().to_dict() == {"NO_APLICA": 431, "REEMBOLSADO": 12, "SIN_REEMBOLSO": 1}
    assert s[s.estado_reembolso == "SIN_REEMBOLSO"].index.tolist() == ["88680179"]
    assert s.monto_en_juego_c.sum() == 3_499_800


def test_menpros_devoluciones(menpros):
    d = menpros.devoluciones
    assert d.estado.value_counts().to_dict() == {
        "COBRADO": 541, "COBRO_MAYOR_AL_FLETE": 10, "DIFERENCIA_TARIFA": 8, "COBRO_ANTICIPADO": 6, "COBRADO_SIN_TARIFA": 4}
    assert set(d[d.estado == "COBRO_MAYOR_AL_FLETE"].transportadora) == {"COORDINADORA"}
    assert d[d.estado == "COBRO_MAYOR_AL_FLETE"].monto_en_juego_c.sum() == 1_045_626


def test_proveeduria_c0_y_ganancia(proveeduria):
    assert proveeduria.chequeos[0].estado == "EN_ORDEN"
    assert proveeduria.ganancia.estado.value_counts().to_dict() == {
        "PAGADA": 5053, "NO_APLICA": 3493, "PAGADA_SIN_VALIDAR": 130, "PAGO_POSTERIOR_AL_REPORTE": 120, "REVERSADA": 1}


def test_proveeduria_fulfillment(proveeduria):
    f = proveeduria.fulfillment
    assert f.estado.value_counts().to_dict() == {
        "COBRADO": 6633, "NO_APLICA": 1948, "COBRO_POSTERIOR_AL_REPORTE": 202, "DUPLICADO": 12, "REVERSADO": 2}
    assert f[f.estado == "DUPLICADO"].monto_en_juego_c.sum() == 3_000_000


def test_pagos(entorno):
    p = _json_runtime("parametros_wallet_pagos.json")
    r = conciliar_wallet_pagos(pd.read_excel(PAGOS), p, entorno["catalogo"], p["wallets"][0], "2026-09-01", "2026-09-30")
    assert r.chequeos[0].estado == "EN_ORDEN"
    assert r.resumen["sin_concepto"] == 0
    assert len(r.movimientos) == 13


def test_proveeduria_ordenes_de_otra_tienda(proveeduria):
    f = proveeduria.fuera_del_reporte
    otra = f[f.motivo == "ORDEN_DE_OTRA_TIENDA"].groupby("concepto").neto_c.agg(["size", "sum"])
    assert otra.loc["COBRO_FULFILLMENT"].tolist() == [13, -3_250_000]
    assert otra.loc["GANANCIA_PROVEEDOR"].tolist() == [10, 13_000_000]


# ------------------------------------------------- hallazgos que llegan a la bandeja (PANTALLA_WALLETS.md §2.2)


def _gravedades(hallazgos):
    out = {}
    for h in hallazgos:
        out[h.gravedad] = out.get(h.gravedad, 0) + 1
    return out


def test_menpros_no_encontradas_separa_reemplazadas(menpros):
    [h] = [h for h in hallazgos_tienda(menpros) if h.codigo == "TIENDA_FUERA_NO_ENCONTRADA"]
    assert h.gravedad == "MEDIO"
    assert h.evidencia["movimientos"] == 180
    assert h.evidencia["reemplazadas"]["movimientos"] == 64
    assert h.evidencia["otros"]["movimientos"] == 116


def test_proveeduria_no_encontradas_sin_reemplazadas(proveeduria):
    [h] = [h for h in hallazgos_tienda(proveeduria) if h.codigo == "TIENDA_FUERA_NO_ENCONTRADA"]
    assert h.evidencia["reemplazadas"]["movimientos"] == 0
    assert h.evidencia["otros"]["movimientos"] == 109


def test_ordenes_anteriores_al_reporte_son_un_solo_hallazgo(menpros, proveeduria):
    for r, n in ((menpros, 2246), (proveeduria, 2570)):
        [h] = [h for h in hallazgos_tienda(r) if h.codigo == "TIENDA_FUERA_ORDEN_ANTERIOR_AL_REPORTE"]
        assert h.gravedad == "INFORMATIVO"
        assert h.descripcion.startswith(f"{n} movimientos de órdenes anteriores al reporte")


def test_volumen_de_la_bandeja_de_septiembre(menpros, proveeduria):
    # Menpros: T2 1 crítico; T3 18 medios + 6 informativos; NO_ENCONTRADA 1; anteriores 1; 10 movimientos.
    assert _gravedades(hallazgos_tienda(menpros)) == {"CRITICO": 1, "MEDIO": 19, "INFORMATIVO": 7, "REVISAR": 10}
    # Proveeduría: T4 12 duplicados; otra tienda 24; NO_ENCONTRADA 1; anteriores 1; 10 movimientos.
    assert _gravedades(hallazgos_tienda(proveeduria)) == {"MEDIO": 37, "INFORMATIVO": 1, "REVISAR": 10}
