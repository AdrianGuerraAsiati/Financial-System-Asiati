"""Extracción preliminar UBL; un PDF o imagen exige entrada verificada por usuario."""
from xml.etree import ElementTree as ET


def _texto(elem: ET.Element, nombre: str) -> str | None:
    for x in elem.iter():
        if x.tag.rsplit("}", 1)[-1] == nombre and x.text and x.text.strip():
            return x.text.strip()
    return None


def extraer_ubl(data: bytes) -> dict:
    if len(data) > 3_000_000 or b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("XML no admitido (tamaño, DTD o entidades).")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError("XML ilegible.") from exc
    if root.tag.rsplit("}", 1)[-1] != "Invoice":
        raise ValueError("Se necesita un XML UBL tipo Invoice; otros formatos requieren captura manual.")
    campos = {
        "numero": _texto(root, "ID"),
        "fecha_emision": _texto(root, "IssueDate"),
        "fecha_vencimiento": _texto(root, "DueDate"),
    }
    for x in root.iter():
        if x.tag.rsplit("}", 1)[-1] == "AccountingSupplierParty":
            campos["proveedor"] = _texto(x, "RegistrationName") or _texto(x, "Name")
            break
    for x in root.iter():
        if x.tag.rsplit("}", 1)[-1] == "LegalMonetaryTotal":
            for y in x:
                if y.tag.rsplit("}", 1)[-1] == "PayableAmount" and y.text:
                    campos["monto"] = y.text.strip()
                    campos["moneda"] = y.attrib.get("currencyID", "COP")
                    break
            break
    for x in root.iter():
        if x.tag.rsplit("}", 1)[-1] == "InvoiceLine":
            campos["descripcion"] = _texto(x, "Description") or _texto(x, "Name")
            break
    return {
        "campos": {k: v for k, v in campos.items() if v},
        "advertencias": ["Confirma el resultado contra la factura. No se infieren fechas ausentes."]
    }
