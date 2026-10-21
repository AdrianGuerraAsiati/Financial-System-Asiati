"""Navegación por tareas de Cartera sin alterar controles, IDs o permisos."""
from pathlib import Path
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from app.main import app

BASE = Path(__file__).resolve().parents[1]


def test_recursos_de_navegacion_y_orden_de_carga():
    client = TestClient(app)
    html = client.get("/").text
    assert 'href="/static/cartera_navegacion.css"' in html
    assert 'src="/static/cartera_navegacion.js"' in html
    assert html.index('src="/static/cartera_navegacion.js"') < html.index(
        'src="/static/app.js"'
    )
    js = client.get("/static/cartera_navegacion.js")
    assert js.status_code == 200
    for name in ("operaciones", "proyeccion", "mora", "documentos",
                 "comprobantes", "fuentes", "aportes", "tabla", "comerciales"):
        assert '"' + name + '"' in js.text
    assert 'role", "tablist"' in js.text
    assert 'role", "tabpanel"' in js.text
    assert "navegarA(id)" in js.text
    assert "root.appendChild(panel)" in js.text
    css = client.get("/static/cartera_navegacion.css")
    assert css.status_code == 200
    assert ".cartera-vistas-nav" in css.text
    assert ".cartera-vistas-panel[hidden]" in css.text
    assert "max-height:min(62vh,640px)" in css.text


def test_no_se_modifican_las_rutas_ni_el_alcance_de_los_datos():
    app_js = (BASE / "app/web/app.js").read_text("utf-8")
    assert 'window.ASIATI_CARTERA_NAV?.configurarAcceso(sesion)' in app_js
    assert '"cartera.ver"] === "TODAS"' in (
        BASE / "app/web/cartera_navegacion.js"
    ).read_text("utf-8")
    assert "consultada !== empresaId() || solicitud !== carteraDetalleSolicitud" in app_js
    assert "panel.scrollIntoView" in app_js
    assert "formComprobante.elements.oc.value = \"\"" in app_js


@pytest.mark.skipif(shutil.which("node") is None, reason="Node no disponible")
def test_navegacion_reubica_paneles_reales_y_aplica_permiso_global():
    harness = r'''
const fs=require("node:fs");
const vm=require("node:vm");
const assert=require("node:assert/strict");
const source=fs.readFileSync(process.argv[1],"utf8");
const lookup=new Map();
class E {
 constructor(tag="div",id="") {
   this.tagName=tag;this.id=id;this.children=[];this.parentElement=null;
   this.hidden=false;this.attributes={};this.events={};this.tabIndex=0;
   this.classNames=new Set();this.focused=false;this.textContent="";
   this.classList={
     contains:(name)=>this.classNames.has(name),
     add:(name)=>this.classNames.add(name),
     toggle:(name,yes)=>{if(yes)this.classNames.add(name);else this.classNames.delete(name)}
   };
   if(id)lookup.set(id,this);
 }
 appendChild(e){
   if(e.parentElement) {
     const idx=e.parentElement.children.indexOf(e);
     if(idx>=0)e.parentElement.children.splice(idx,1);
   }
   this.children.push(e);e.parentElement=this;
   if(e.id)lookup.set(e.id,e);return e;
 }
 append(...elements){for(const el of elements)this.appendChild(el)}
 insertAdjacentElement(where,e){
   if(where!=="afterend")throw Error("unsupported");
   const parent=this.parentElement;
   const idx=parent.children.indexOf(this);
   if(e.parentElement){const i=e.parentElement.children.indexOf(e);if(i>=0)e.parentElement.children.splice(i,1)}
   parent.children.splice(idx+1,0,e);e.parentElement=parent;if(e.id)lookup.set(e.id,e);
 }
 setAttribute(key,value){this.attributes[key]=value}
 getAttribute(key){return this.attributes[key]??null}
 addEventListener(key,fn){this.events[key]=fn}
 querySelector(selector){
   if(selector===".intro")return this.children.find(x=>x.classNames.has("intro"))||null;
   return null;
 }
 closest(selector){
   if(selector!=="[hidden]")return null;
   let node=this;while(node){if(node.hidden)return node;node=node.parentElement}
   return null;
 }
 scrollIntoView(){}
 focus(){this.focused=true}
}
const root=new E("div","vista-cartera");
const intro=new E("section");intro.classNames.add("intro");root.appendChild(intro);
function panel(id){
 const el=new E("section",id);root.appendChild(el);return el;
}
for(const id of ["cartera-fuente","cartera-snapshots","cartera-calidad",
 "operaciones","detalle-operacion","cartera-drive-panel",
 "cartera-mora","cartera-proyeccion","cartera-aportes",
 "cartera-dispersion"])panel(id);
const grid=new E("section");grid.classNames.add("grid-two");root.appendChild(grid);
const pending=new E("section","comprobantes-pendientes");grid.appendChild(pending);
function findById(node,id) {
 if(node.id===id)return node;
 for(const child of node.children){const found=findById(child,id);if(found)return found;}
 return null;
}
const document={
 getElementById:(id)=>lookup.get(id)||findById(root,id),
 createElement:(tag)=>new E(tag)
};
const window={events:{},addEventListener(k,fn){this.events[k]=fn}};
vm.runInNewContext(source,{document,window,location:{hash:""}});
const nav=window.ASIATI_CARTERA_NAV;
assert.ok(nav);
assert.equal(lookup.get("detalle-operacion").hidden,true);
assert.equal(lookup.get("cartera-vista-operaciones").hidden,false);
assert.equal(lookup.get("cartera-vista-proyeccion").hidden,true);
assert.equal(lookup.get("operaciones").parentElement.id,"cartera-vista-operaciones");
assert.equal(lookup.get("detalle-operacion").parentElement.id,"cartera-vista-operaciones");
assert.equal(grid.parentElement.id,"cartera-vista-comprobantes");
nav.configurarAcceso({permisos:{"cartera.ver":"EMPRESA"}});
assert.equal(lookup.get("cartera-tab-documentos").hidden,true);
nav.activar("documentos");
assert.equal(lookup.get("cartera-vista-operaciones").hidden,false);
nav.configurarAcceso({permisos:{"cartera.ver":"TODAS"}});
nav.activar("documentos");
assert.equal(lookup.get("cartera-vista-documentos").hidden,false);
nav.activar("proyeccion");
assert.equal(lookup.get("cartera-vista-proyeccion").hidden,false);
assert.equal(lookup.get("cartera-subvista-aportes").hidden,false);
assert.equal(lookup.get("cartera-subvista-tabla").hidden,true);
nav.activarSubvista("comerciales");
assert.equal(lookup.get("cartera-subvista-comerciales").hidden,false);
assert.equal(lookup.get("cartera-dispersion").parentElement.id,"cartera-subvista-comerciales");
nav.navegarA("cartera-proyeccion");
assert.equal(lookup.get("cartera-subvista-tabla").hidden,false);
nav.activar("fuentes");
assert.equal(lookup.get("cartera-fuente").parentElement.id,"cartera-vista-fuentes");
assert.equal(lookup.get("cartera-calidad").parentElement.id,"cartera-vista-fuentes");
assert.equal(lookup.get("cartera-vista-fuentes").hidden,false);
assert.equal(lookup.get("cartera-tab-fuentes").attributes["aria-selected"],"true");
'''
    result=subprocess.run(
        ["node","-e",harness,str(BASE/"app/web/cartera_navegacion.js")],
        capture_output=True,text=True,timeout=25,check=False
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
