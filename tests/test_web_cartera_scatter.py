"""Gráfica de dispersión comercial: contratos de fuente, seguridad y aritmética."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from app.main import app

BASE = Path(__file__).resolve().parents[1]
JS = BASE / "app" / "web" / "cartera_scatter.js"


def test_panel_y_script_estan_en_cartera_sin_dependencias_cdn():
    html = TestClient(app).get("/").text
    assert 'id="cartera-dispersion"' in html
    assert 'id="cartera-dispersion-grafica"' in html
    assert 'id="cartera-dispersion-desde"' in html
    assert 'id="cartera-dispersion-hasta"' in html
    assert 'id="cartera-dispersion-buscar"' in html
    assert 'id="cartera-dispersion-tabla-body"' in html
    assert 'id="cartera-dispersion-prev"' in html
    assert 'id="cartera-dispersion-next"' in html
    assert 'id="cartera-dispersion-kpi-comerciales"' in html
    assert 'id="cartera-dispersion-kpi-monto"' in html
    assert 'id="cartera-dispersion-kpi-registros"' in html
    assert '<details class="cartera-scatter-tabla">' in html
    assert html.index('src="/static/cartera_scatter.js"') < html.index(
        'src="/static/app.js"'
    )
    assert "recaudos efectuados" in html


def test_componente_con_datos_reales_y_respaldo_accesible():
    response = TestClient(app).get("/static/cartera_scatter.js")
    assert response.status_code == 200
    javascript = response.text
    for fragmento in (
        "BigInt(", "agruparFilas(", "setData(", "limpiarDatos(",
        "PROYECCIONES", 'role: "button"', "keydown",
        "comercialElegido", "aria-label", "cartera-dispersion-tabla-body"
    ):
        assert fragmento in javascript
    for nombre in ("colocarEtiquetas(", "actualizarMetricas(", "pasoMonto("):
        assert nombre in javascript
    assert "const width = 960, height = 316" in javascript
    assert "Math.random()" not in javascript
    assert "fetch(" not in javascript
    source = (BASE / "app" / "web" / "app.js").read_text("utf-8")
    assert 'window.ASIATI_SCATTER?.setData(rows, {empresaId: consultada})' in source
    assert "solicitud !== carteraProyeccionSolicitud" in source
    assert "window.ASIATI_SCATTER?.limpiarDatos" in source
    css = TestClient(app).get("/static/asiati_v2.css").text
    assert "#cartera-dispersion .cartera-scatter-grafica" in css


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js no está disponible")
def test_agrupacion_js_suma_decimales_y_no_duplica_ocs():
    # Se ejecuta el JavaScript real sin navegador usando elementos DOM simulados.
    harness = r'''
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const code = fs.readFileSync(process.argv[1], "utf8");
function element() {
  return {
    value: "", textContent: "", classList: {toggle() {}},
    addEventListener() {}, replaceChildren() {}, appendChild() {},
    querySelectorAll() {return []}, setAttribute() {}
  };
}
const dom = new Map();
const document = {
  getElementById(id) {
    if (!dom.has(id)) dom.set(id, element());
    return dom.get(id);
  },
  createElement() {return element()},
  createElementNS() {return element()}
};
dom.set("cartera-dispersion-tamano", {...element(), value: "20"});
const window = {};
vm.runInNewContext(code, {document, window});
const aggregate = window.ASIATI_SCATTER.agruparFilas;
const rows = [
 {comercial:"ALFA", oc:" GM607 ", monto:"0.10", mes:"2026-09"},
 {comercial:"alfa", oc:"GM607", monto:"0.20", mes:"2026-10"},
 {comercial:"ALFA", oc:"", monto:"5.00", mes:"2026-10"},
 {comercial:"BÉTA", oc:"GM611", monto:"2.05", mes:"2026-10"},
 {comercial:"", oc:"GM612", monto:"3.00", mes:"2026-10"},
 {comercial:"ALFA", oc:"GM613", monto:"-1.00", mes:"2026-10"},
 {comercial:"ALFA", oc:"GM614", monto:"1.00", mes:"2026-11"}
];
const all = aggregate(rows);
assert.equal(all.puntos.length, 3);
const alfa = all.puntos.find((p) => p.comercial === "ALFA");
assert.equal(alfa.ocs, 2);
assert.equal(alfa.registros, 4);
assert.equal(alfa.sinOc, 1);
assert.equal(alfa.monto, "6.30");
assert.equal(alfa.montoExacto, "USD 6,30");
assert.equal(all.registrosExcluidos, 1);
const beta = aggregate(rows, {desde:"2026-10", hasta:"2026-10", buscar:"beta"});
assert.equal(beta.puntos.length, 1);
assert.equal(beta.puntos[0].comercial, "BÉTA");
assert.equal(beta.puntos[0].ocs, 1);
assert.equal(beta.puntos[0].monto, "2.05");
const september = aggregate(rows, {desde:"2026-09", hasta:"2026-09"});
assert.equal(september.puntos[0].monto, "0.10");
assert.equal(september.puntos[0].registros, 1);
const big = aggregate([{comercial:"ALFA", oc:"GM1", monto:"9007199254740993.11", mes:"2026-10"}]);
assert.equal(big.puntos[0].monto, "9007199254740993.11");
assert.equal(big.puntos[0].montoExacto, "USD 9.007.199.254.740.993,11");
const unassigned = all.puntos.find((p) => p.comercial === "SIN ASIGNAR");
assert.equal(unassigned.ocs, 1);
assert.equal(unassigned.monto, "3.00");
// Escala de 125,7 mil debe finalizar en 150 mil, no desperdiciar espacio hasta 250 mil.
assert.equal(window.ASIATI_SCATTER.pasoMonto(125694.90) * 5, 150000);
assert.equal(window.ASIATI_SCATTER.pasoMonto(40908.70) * 5, 50000);
// Los resúmenes siempre se derivan de los registros reales que alimentan el gráfico.
window.ASIATI_SCATTER.setData(rows, {empresaId: 17});
assert.equal(dom.get("cartera-dispersion-kpi-comerciales").textContent, "3");
assert.equal(dom.get("cartera-dispersion-kpi-monto").textContent, "11,35");
assert.equal(dom.get("cartera-dispersion-kpi-registros").textContent, "6");
assert.equal(dom.get("cartera-dispersion-tabla-titulo").textContent,
  "Ver datos exactos por comercial (3)");
window.ASIATI_SCATTER.limpiarDatos();
assert.equal(dom.get("cartera-dispersion-kpi-comerciales").textContent, "—");
assert.equal(dom.get("cartera-dispersion-kpi-monto").textContent, "—");
assert.equal(dom.get("cartera-dispersion-kpi-registros").textContent, "—");
'''
    result = subprocess.run(
        ["node", "-e", harness, str(JS)],
        capture_output=True, text=True, timeout=20, check=False
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
