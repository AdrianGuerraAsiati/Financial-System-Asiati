"""Contrato de interfaz ASIATI 360: indicadores reales y diseño transversal."""
from fastapi.testclient import TestClient

from app.main import app


def test_inicio_carga_tema_y_graficas_antes_del_controlador():
    respuesta = TestClient(app).get("/")
    assert respuesta.status_code == 200
    html = respuesta.text
    assert 'href="/static/asiati_v2.css"' in html
    assert 'id="inicio-analitica"' in html
    assert html.index('src="/static/financial_charts.js"') < html.index('src="/static/app.js"')


def test_tema_financiero_compartido_no_sustituye_identidad_asiati():
    respuesta = TestClient(app).get("/static/asiati_v2.css")
    assert respuesta.status_code == 200
    css = respuesta.text
    assert "--finance-canvas: #fafaf9" in css
    assert "--finance-signal: #3ba6f1" in css
    assert "#app-shell .sidebar" in css
    assert ".finance-chart-grid" in css
    assert "prefers-reduced-motion" in css


def test_graficas_usar_solo_datos_del_dashboard_y_revelar_procedencia():
    respuesta = TestClient(app).get("/static/financial_charts.js")
    assert respuesta.status_code == 200
    js = respuesta.text
    assert "renderDashboard(respuesta)" in js
    assert "último snapshot de Cartera" in js
    assert "hallazgos de conciliación" in js
    assert "Sin snapshot de Cartera" in js
    assert "aria-pressed" in js
    assert "Ver tabla de datos" in js
    assert "textContent" in js
    assert "dataset demo" not in js.lower()
    assert "Math.random" not in js


def test_cambio_empresa_descarta_respuesta_de_dashboard_anterior():
    respuesta = TestClient(app).get("/static/app.js")
    assert respuesta.status_code == 200
    js = respuesta.text
    assert "const empresaConsultada = empresaId();" in js
    assert "if (empresaConsultada !== empresaId()) return;" in js
    assert "ASIATI_FINANCIAL_CHARTS?.renderDashboard(data)" in js
