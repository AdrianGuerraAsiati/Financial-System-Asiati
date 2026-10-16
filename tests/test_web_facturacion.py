"""Contrato visual V1: Facturación es la vista de cuentas por pagar, sin crear un motor nuevo."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app/web/index.html").read_text(encoding="utf-8")
JS = (ROOT / "app/web/tesoreria.js").read_text(encoding="utf-8")


def test_facturacion_es_la_vista_de_cuentas_por_pagar():
    assert '<span class="nav-label">Facturación</span>' in HTML
    assert 'Facturación · Cuentas por pagar' in HTML
    assert '<h2>Facturas de compra y pagos</h2>' in HTML
    # Mantener IDs/URLs existentes: no crear un quinto motor.
    assert 'id="nav-tesoreria"' in HTML
    assert 'id="vista-tesoreria"' in HTML


def test_factura_y_pago_tienen_formularios_separados_y_comprobantes():
    assert 'id="tesoreria-nueva"' in HTML
    assert 'name="archivo" type="file"' in HTML
    assert 'id="tesoreria-pagar"' in HTML
    assert 'name="fecha" type="date" required' in HTML
    assert 'name="monto" type="number" min="0.01" step="0.01" required' in HTML
    assert 'name="comprobante" type="file"' in HTML
    assert '"/api/v1/tesoreria/facturas"' in JS
    assert '"/pagos"' in JS
    assert 'datos.append("empresa_id", String(empresaId()))' in JS
