"""Operaciones ordenables y detalles de Cartera en ventanas sin datos financieros inventados."""
from pathlib import Path
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]


def test_operaciones_ordenables_antes_de_paginacion_y_enlaces_modal():
    client=TestClient(app)
    html=client.get("/").text
    js=client.get("/static/app.js").text
    sort=client.get("/static/cartera_sort.js").text
    modal=client.get("/static/modal.js").text
    assert client.get("/static/modal.css").status_code == 200
    assert sort and modal
    assert 'id="cartera-operaciones-orden"' in html
    assert 'id="cartera-operaciones-direccion"' in html
    for field in ("oc","cliente","estado","valor"):
        assert 'data-cartera-sort="'+field+'"' in html
        assert 'value="'+field+'"' in html
    assert html.index('src="/static/modal.js"') < html.index('src="/static/app.js"')
    assert html.index('src="/static/cartera_sort.js"') < html.index('src="/static/app.js"')
    assert "const filasOrdenadas = window.ASIATI_CARTERA_SORT.ordenar(" in js
    assert "filasOrdenadas.slice(inicio, inicio + porPagina)" in js
    assert 'boton.dataset.carteraSort' in js
    assert 'aria-sort' in js
    assert 'class="cartera-aportes-detalle" id="cartera-aportes-detalle" hidden' in html


def test_todos_los_detalles_usan_un_solo_dialog_y_limpian_por_empresa():
    client=TestClient(app)
    modal=client.get("/static/modal.js").text
    drive=client.get("/static/cartera_drive.js").text
    aportes=client.get("/static/cartera_aportes.js").text
    appjs=client.get("/static/app.js").text
    assert 'document.createElement("dialog")' in modal
    assert 'node.showModal()' in modal
    assert 'node.addEventListener("close"' in modal
    assert 'if(event.target===node)close()' in modal
    assert 'closeButton.addEventListener("click",()=>close())' in modal
    assert 'returnFocus.focus({preventScroll:true})' in modal
    assert "originalParent.insertBefore(" in modal  # Restaurar IDs/handlers.
    assert "document.body.classList.add" in modal
    assert "window.ASIATI_MODAL.open(" in drive
    assert "window.ASIATI_MODAL.open(" in aportes
    assert "window.ASIATI_MODAL.open(" in appjs
    assert "data-cartera-comprobante" in appjs
    assert "window.ASIATI_MODAL?.close();" in appjs
    assert "const solicitudSoporte = ++consultaSoporte;" in drive
    assert "const solicitud = ++carteraDetalleSolicitud;" in appjs
    assert "if (consultada !== empresaId() || solicitud !== carteraDetalleSolicitud)" in appjs
    assert "Pagado confirmado: sin verificar" in aportes
    assert "verGmsDelCliente" in appjs
    assert 'data-cliente=' in appjs
    assert "La coincidencia por cliente no demuestra a cuál GM" in appjs
    assert "Faltante real: no calculable" in aportes


@pytest.mark.skipif(shutil.which("node") is None, reason="Node no disponible")
def test_orden_natural_decimal_y_estabilidad_ante_paginacion():
    harness=r'''
const fs=require("node:fs");
const vm=require("node:vm");
const assert=require("node:assert/strict");
const window={};
vm.runInNewContext(fs.readFileSync(process.argv[1],"utf8"),{window,Intl,BigInt});
const sort=window.ASIATI_CARTERA_SORT;
const rows=[
 {oc:"GM10",cliente:"Beta",estado:"ENVIADO",valor:"9.99"},
 {oc:"GM2",cliente:"Árbol",estado:"PENDIENTE",valor:"120.00"},
 {oc:"GM1",cliente:"Árbol",estado:"ENVIADO",valor:"10.01"},
 {oc:"GM20",cliente:"Cliente",estado:"ENVIADO",valor:"100.10"},
 {oc:"GM3",cliente:"Beta",estado:"PENDIENTE",valor:"100.01"},
 {oc:"GM4",cliente:"Beta",estado:"PENDIENTE",valor:null}
];
function o(field,direction){
 return sort.ordenar(rows,field,direction).map(r=>r.oc).join(",");
}
assert.equal(o("oc","asc"),"GM1,GM2,GM3,GM4,GM10,GM20");
assert.equal(o("oc","desc"),"GM20,GM10,GM4,GM3,GM2,GM1");
assert.equal(o("cliente","asc"),"GM1,GM2,GM3,GM4,GM10,GM20");
assert.equal(o("estado","asc"),"GM1,GM10,GM20,GM2,GM3,GM4");
assert.equal(o("valor","asc"),"GM10,GM1,GM3,GM20,GM2,GM4");
assert.equal(o("valor","desc"),"GM2,GM20,GM3,GM1,GM10,GM4");
assert.equal(sort.dineroCentavos("1.234,50"),123450n);
assert.equal(sort.dineroCentavos("1,234.50"),123450n);
assert.equal(sort.dineroCentavos("-3.05"),-305n);
assert.equal(sort.dineroCentavos("mal"),null);
assert.equal(rows[0].oc,"GM10"); // No muta fuente.
const page1=sort.ordenar(rows,"oc","asc").slice(0,3).map(r=>r.oc).join(",");
const page2=sort.ordenar(rows,"oc","asc").slice(3,6).map(r=>r.oc).join(",");
assert.equal(page1,"GM1,GM2,GM3");
assert.equal(page2,"GM4,GM10,GM20");
'''
    p=subprocess.run(["node","-e",harness,str(ROOT/"app/web/cartera_sort.js")],
                     capture_output=True,text=True,timeout=20,check=False)
    assert p.returncode == 0,p.stdout+"\n"+p.stderr
