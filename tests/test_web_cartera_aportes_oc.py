"""Proyecciones por OC: aportes fechados, sumas exactas y aislamiento de fuente."""
from pathlib import Path
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient
from app.main import app

ROOT = Path(__file__).resolve().parents[1]


def test_aportes_vista_de_cartera_y_sin_fuentes_de_recaudos():
    pagina = TestClient(app).get("/").text
    assert 'id="cartera-aportes"' in pagina
    for campo in (
        "cartera-aportes-buscar", "cartera-aportes-comercial",
        "cartera-aportes-desde", "cartera-aportes-hasta",
        "cartera-aportes-lista", "cartera-aportes-detalle-contenido",
        "cartera-aportes-monto", "cartera-aportes-anterior",
        "cartera-aportes-meses", "cartera-aportes-orden",
        "cartera-aportes-multiples",
    ):
        assert 'id="' + campo + '"' in pagina
    assert pagina.index('src="/static/cartera_aportes.js"') < pagina.index(
        'src="/static/app.js"'
    )
    assert "No equivale a pagos recibidos" in pagina


def test_proyeccion_alimenta_aportes_sin_llamadas_extra():
    js = TestClient(app).get("/static/app.js")
    assert js.status_code == 200
    assert "window.ASIATI_APORTES?.setData(rows, {empresaId: consultada})" in js.text
    assert "window.ASIATI_APORTES?.limpiarDatos" in js.text
    aportes = TestClient(app).get("/static/cartera_aportes.js")
    assert aportes.status_code == 200
    for marca in ("BigInt(", "agrupar(", "setData(", "limpiarDatos(", "porFecha",
                  "resumirMeses(", "ordenarOcs(", "pintarMeses(", "porcentajeTexto("):
        assert marca in aportes.text
    assert "fetch(" not in aportes.text
    assert "Math.random()" not in aportes.text


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js no disponible")
def test_agrupacion_preserva_aportes_por_fecha_y_centavos_exactos():
    harness = r'''
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const source = fs.readFileSync(process.argv[1], "utf8");
const elements = new Map();
function element() {
 return {
   value:"", textContent:"", style:{}, children:[], classList:{add(){},remove(){},toggle(){}},
   setAttribute(){}, addEventListener(){}, append(...items){this.children.push(...items)},
   appendChild(child){this.children.push(child)}, replaceChildren(...items){this.children=[...items]},
   querySelectorAll(){return []}
 };
}
const document = {
 getElementById(id) { if(!elements.has(id))elements.set(id,element());return elements.get(id); },
 createElement(){return element()}
};
function Option(text,value){this.text=text;this.value=value;}
elements.set("cartera-aportes-comercial", {
 ...element(), add(option){this.children.push(option)},
 replaceChildren(...items){this.children=[...items]}
});
const window={};
vm.runInNewContext(source,{document,window,Option});
const agg=window.ASIATI_APORTES.agrupar;
const rows=[
 {oc:" OC-001 ",cliente:"Árbol SA",comercial:"ANGEL",fecha:"2026-10-01",monto:"20.00"},
 {oc:"oc-001",cliente:"Árbol SA",comercial:"ANGEL",fecha:"2026-10-01",monto:"10.30"},
 {oc:"OC-001",cliente:"Árbol SA",comercial:"ANGEL",fecha:"2026-11-12",monto:"4.70"},
 {oc:"OC-002",cliente:"Beta",comercial:"SEBASTIAN",fecha:"2026-10-02",monto:"5.00"},
 {oc:"",cliente:"Beta",comercial:"ANGEL",fecha:"2026-10-03",monto:"8.00"},
 {oc:"OC-001",cliente:"Árbol SA",comercial:"ANGEL",fecha:"2026-10-02",monto:"-3.00"}
];
const all=agg(rows);
assert.equal(all.items.length,2);
assert.equal(all.total,4000n);
assert.equal(all.sinOC,1);
assert.equal(all.omitidos,1);
const uno=all.items.find(x=>x.oc==="OC-001");
assert.equal(uno.monto,3500n);
assert.equal(uno.aportes.length,2);
assert.equal(uno.aportes[0].fecha,"2026-10-01");
assert.equal(uno.aportes[0].monto,3030n);
assert.equal(uno.aportes[0].filas,2);
assert.equal(uno.aportes[1].monto,470n);
assert.equal(uno.filas,3);
const filtered=agg(rows,{desde:"2026-10-01",hasta:"2026-10-31",buscar:"arbol",comercial:"ANGEL"});
assert.equal(filtered.items.length,1);
assert.equal(filtered.items[0].monto,3030n);
const other=agg(rows,{comercial:"SEBASTIAN"});
assert.equal(other.items.length,1);
assert.equal(other.items[0].monto,500n);
const meses = window.ASIATI_APORTES.resumirMeses(all.items);
assert.equal(meses.length,2);
assert.equal(meses[0].mes,"2026-10");
assert.equal(meses[0].monto,3530n);
assert.equal(meses[0].ocs,2);
assert.equal(meses[0].registros,3);
assert.equal(meses[1].mes,"2026-11");
assert.equal(meses[1].monto,470n);
assert.equal(meses[1].ocs,1);
const temporal = window.ASIATI_APORTES.ordenarOcs(all.items,"fecha_desc");
assert.equal(temporal[0].oc,"OC-001");
const primera = window.ASIATI_APORTES.ordenarOcs(all.items,"fecha_asc");
assert.equal(primera[0].oc,"OC-001");
const invertidas = [
 {oc:"OC-009",aportes:[{fecha:"2026-10-25",monto:100n}],monto:100n},
 {oc:"OC-008",aportes:[{fecha:"2026-10-01",monto:200n}],monto:200n}
];
assert.equal(window.ASIATI_APORTES.ordenarOcs(invertidas,"fecha_asc")[0].oc,"OC-008");
assert.equal(window.ASIATI_APORTES.ordenarOcs(invertidas,"fecha_desc")[0].oc,"OC-009");
window.ASIATI_APORTES.setData(rows,{empresaId:22});
assert.equal(elements.get("cartera-aportes-ocs").textContent,"2");
assert.equal(elements.get("cartera-aportes-registros").textContent,"4");
assert.equal(elements.get("cartera-aportes-monto").textContent,"40,00");
assert.equal(elements.get("cartera-aportes-meses").children.length,1);
assert.equal(elements.get("cartera-aportes-detalle-contenido").children.length > 3,true);
const multi = elements.get("cartera-aportes-multiples");
multi.checked=true;
window.ASIATI_APORTES.setData(rows,{empresaId:22});
assert.equal(elements.get("cartera-aportes-ocs").textContent,"1");
assert.equal(elements.get("cartera-aportes-monto").textContent,"35,00");
multi.checked=false;
window.ASIATI_APORTES.limpiarDatos();
assert.equal(elements.get("cartera-aportes-ocs").textContent,"—");
assert.equal(elements.get("cartera-aportes-monto").textContent,"—");
'''
    p = subprocess.run(
        ["node", "-e", harness, str(ROOT / "app/web/cartera_aportes.js")],
        capture_output=True, text=True, check=False, timeout=20
    )
    assert p.returncode == 0, p.stdout + "\n" + p.stderr
