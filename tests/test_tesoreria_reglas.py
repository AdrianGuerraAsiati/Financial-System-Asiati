"""Guardas financieras para la V1 de facturas de compra."""
from datetime import date
from decimal import Decimal
import pytest

from app.motores.tesoreria.reglas import estado_factura
from app.motores.tesoreria.extraccion import extraer_ubl


def test_factura_radica_pendiente_y_sin_pago() -> None:
    estado = estado_factura(Decimal("1000.00"), [], date(2026, 11, 1), date(2026, 10, 13))
    assert estado == {"estado": "PENDIENTE", "alerta": None, "pagado": "0.00", "saldo": "1000.00"}


def test_pago_parcial_y_completo() -> None:
    parcial = estado_factura(Decimal("1000.00"), [Decimal("200.00")], date(2026, 10, 1), date(2026, 10, 13))
    assert parcial["estado"] == "PARCIAL"
    assert parcial["saldo"] == "800.00"
    final = estado_factura(Decimal("1000.00"), [Decimal("200.00"), Decimal("800.00")], None, date(2026, 10, 13))
    assert final["estado"] == "PAGADA"
    assert final["alerta"] is None


def test_sin_fecha_vencimiento_requiere_revision() -> None:
    estado = estado_factura(Decimal("1000.00"), [], None, date(2026, 10, 13))
    assert estado["estado"] == "PENDIENTE_VALIDACION"
    assert estado["alerta"] == "REVISAR_VENCIMIENTO"


def test_rechaza_sobrepago() -> None:
    with pytest.raises(ValueError, match="exceden"):
        estado_factura(Decimal("100.00"), [Decimal("200.00")], None, date(2026, 10, 13))


UBL = b'''<?xml version="1.0"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
<cbc:ID>FE-1382</cbc:ID><cbc:IssueDate>2026-09-01</cbc:IssueDate>
<cbc:DueDate>2026-09-30</cbc:DueDate>
<cac:AccountingSupplierParty><cac:Party><cac:PartyLegalEntity>
<cbc:RegistrationName>Proveedor Prueba</cbc:RegistrationName>
</cac:PartyLegalEntity></cac:Party></cac:AccountingSupplierParty>
<cac:LegalMonetaryTotal><cbc:PayableAmount currencyID="COP">280000.00</cbc:PayableAmount></cac:LegalMonetaryTotal>
<cac:InvoiceLine><cac:Item><cbc:Description>Servicio mensual</cbc:Description></cac:Item></cac:InvoiceLine>
</Invoice>'''


def test_ubl_extrae_vencimiento_y_total_sin_inferencias() -> None:
    datos = extraer_ubl(UBL)["campos"]
    assert datos["fecha_vencimiento"] == "2026-09-30"
    assert datos["monto"] == "280000.00"
    assert datos["proveedor"] == "Proveedor Prueba"
    assert datos["descripcion"] == "Servicio mensual"


def test_xml_con_dtd_bloqueado() -> None:
    with pytest.raises(ValueError, match="DTD"):
        extraer_ubl(b'<!DOCTYPE Invoice [<!ENTITY ejemplo "x">]><Invoice/>')
