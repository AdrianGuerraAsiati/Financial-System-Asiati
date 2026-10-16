"""Regresión real de Recompra Menpros. Fixture y baseline exclusivamente privados.

No basta con el nombre de la wallet: se ejecuta el motor con su configuración
DROPSHIPPER y el reporte original de órdenes, y se contrasta contra un baseline
validado y conservado fuera de Git. Una omisión hace fallar el gate estricto.
"""
import json
import os
from pathlib import Path

import pandas as pd
import pytest

from app.motores.conciliacion_wallets.plataforma.hallazgos import hallazgos_tienda
from app.motores.conciliacion_wallets.tiendas import conciliar_wallet_tienda
from app.motores.conciliacion_wallets.wiilog.integracion import resolver_identificador_wallet


RAIZ = Path(__file__).resolve().parents[2]
CARPETA = RAIZ / "fixtures" / "wallet_tiendas" / "2026-09"
ORDENES_CARPETA = RAIZ / "fixtures" / "wallet_wiilog" / "2026-09"
BASELINE = CARPETA / "expected_recompra_menpros.json"

pytestmark = pytest.mark.fixtures_reales


def _archivo_unico(carpeta, patron):
    archivos = list(carpeta.glob(patron))
    if len(archivos) != 1:
        pytest.skip(f"Se requiere un único archivo privado que coincida con {patron}.")
    return archivos[0]


@pytest.fixture(scope="module")
def caso_recompra():
    if not BASELINE.is_file():
        pytest.skip("Falta el baseline privado validado de Recompra Menpros.")

    email = os.getenv("WIILOG_WALLET_PRINCIPAL_EMAIL", "").strip()
    if not email:
        pytest.skip("Falta la configuración privada WIILOG_WALLET_PRINCIPAL_EMAIL.")

    esperado = json.loads(BASELINE.read_text(encoding="utf-8"))
    claves = {
        "periodo_inicio", "periodo_fin", "corte_ordenes", "c0",
        "movimientos", "ganancia_por_estado", "hallazgos_por_gravedad",
    }
    if not claves.issubset(esperado):
        pytest.fail("Baseline privado incompleto: falta una sección obligatoria.")

    ordenes = _archivo_unico(ORDENES_CARPETA, "ordenes_*.xlsx")
    wallet = _archivo_unico(CARPETA, "wallet_recompra_menpros_*.xlsx")

    docs = RAIZ / "docs" / "motores" / "conciliacion_wallets"
    def parametros(nombre):
        datos = json.loads((docs / nombre).read_text(encoding="utf-8"))
        return resolver_identificador_wallet(datos, wallet_principal_email=email)

    params = parametros("parametros_wallet_tienda.json")
    tiendas = [t for t in params["tiendas"] if t["nombre"] == "Recompra Menpros (Comercial Contact Center)"]
    assert len(tiendas) == 1 and tiendas[0]["rol"] == "DROPSHIPPER"
    tarifas = json.loads((docs / "parametros_wallet_wiilog.json").read_text(encoding="utf-8"))[
        "fulfillment"]["tarifas_por_bodega"]
    resultado = conciliar_wallet_tienda(
        pd.read_excel(ordenes), pd.read_excel(wallet),
        params, parametros("catalogo_conceptos_wallets.json"), tiendas[0],
        esperado["periodo_inicio"], esperado["periodo_fin"],
        tarifas, corte_ordenes=esperado["corte_ordenes"],
    )
    return resultado, esperado


def test_recompra_c0(caso_recompra):
    resultado, esperado = caso_recompra
    assert resultado.chequeos[0].estado == esperado["c0"]["estado"]
    assert resultado.chequeos[0].detalle == esperado["c0"]["detalle"]
    assert resultado.bloqueado is False


def test_recompra_movimientos_y_categorizacion(caso_recompra):
    resultado, esperado = caso_recompra
    movimientos = resultado.movimientos
    esperado_mov = esperado["movimientos"]
    assert len(movimientos) == esperado_mov["total"]
    assert int(movimientos.requiere_revision.sum()) == esperado_mov["requiere_revision"]
    assert int((movimientos.concepto == "SIN_CONCEPTO").sum()) == esperado_mov["sin_concepto"]


def test_recompra_ganancia_y_bandeja(caso_recompra):
    resultado, esperado = caso_recompra
    assert resultado.ganancia.estado.value_counts().to_dict() == esperado["ganancia_por_estado"]
    gravedad = {}
    for hallazgo in hallazgos_tienda(resultado):
        gravedad[hallazgo.gravedad] = gravedad.get(hallazgo.gravedad, 0) + 1
    assert gravedad == esperado["hallazgos_por_gravedad"]
