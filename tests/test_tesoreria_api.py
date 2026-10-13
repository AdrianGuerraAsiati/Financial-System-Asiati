"""Prueba de integración de la V1 de Tesorería con PostgreSQL real."""
from pathlib import Path

from tests.apoyo_auth import cliente_con_rol, cliente_superadmin, crear_empresa
from app.core.usuarios.roles import ROL_ANALISTA_TESORERIA, ROL_TI


def _radicar(cliente, empresa_id: int, numero: str = "FE-100"):
    return cliente.post("/api/v1/tesoreria/facturas", data={
        "empresa_id": str(empresa_id), "numero": numero, "proveedor": "Proveedor Prueba",
        "monto": "1000.00", "moneda": "COP", "descripcion": "Licencia de software",
        "fecha_emision": "2026-10-01", "fecha_vencimiento": "2026-10-31",
    }, files={"archivo": ("factura.pdf", b"%PDF-1.4\nprueba-" + numero.encode(), "application/pdf")})


def test_radicacion_pago_parcial_y_comprobante(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TESORERIA_DOCUMENTOS_DIR", str(tmp_path))
    empresa_id = crear_empresa("Tesorería integración")
    cliente = cliente_superadmin()
    creado = _radicar(cliente, empresa_id)
    assert creado.status_code == 201, creado.text
    factura = creado.json()
    assert factura["fecha_pago_oportuno"] == "2026-10-31"
    assert factura["fecha_pago_real"] is None
    assert factura["estado"] == "PENDIENTE"
    assert factura["saldo"] == "1000.00"
    fid = factura["id"]

    duplicado = _radicar(cliente, empresa_id)
    assert duplicado.status_code == 409

    abono = cliente.post(f"/api/v1/tesoreria/facturas/{fid}/pagos", data={
        "fecha": "2026-10-13", "monto": "400.00", "referencia": "TRX-2026-1"
    }, files={"comprobante": ("soporte.pdf", b"%PDF-1.4\ncomprobante", "application/pdf")})
    assert abono.status_code == 201, abono.text
    assert abono.json()["estado"] == "PARCIAL"
    assert abono.json()["saldo"] == "600.00"
    assert abono.json()["fecha_pago_real"] == "2026-10-13"
    pago_id = abono.json()["pagos"][0]["id"]
    assert cliente.get(f"/api/v1/tesoreria/facturas/{fid}/pagos/{pago_id}/soporte").status_code == 200

    repetido = cliente.post(f"/api/v1/tesoreria/facturas/{fid}/pagos", data={
        "fecha": "2026-10-13", "monto": "100.00"
    }, files={"comprobante": ("soporte.pdf", b"%PDF-1.4\ncomprobante", "application/pdf")})
    assert repetido.status_code == 409

    sobrepago = cliente.post(f"/api/v1/tesoreria/facturas/{fid}/pagos", data={
        "fecha": "2026-10-13", "monto": "601.00"
    }, files={"comprobante": ("otro.pdf", b"%PDF-1.4\notro", "application/pdf")})
    assert sobrepago.status_code == 422

    editado = cliente.patch(f"/api/v1/tesoreria/facturas/{fid}",
                             json={"ciudad": "BOG", "documento_contable": "DS-1"})
    assert editado.status_code == 200, editado.text
    assert editado.json()["ciudad"] == "BOG"
    assert cliente.get(f"/api/v1/tesoreria/facturas/{fid}/documento").status_code == 200


def test_empresa_no_asignada_no_filtra_facturas(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TESORERIA_DOCUMENTOS_DIR", str(tmp_path))
    propia = crear_empresa("Tesorería propia")
    ajena = crear_empresa("Tesorería ajena")
    analista, _ = cliente_con_rol(ROL_ANALISTA_TESORERIA, empresas=(propia,))
    assert analista.get("/api/v1/tesoreria/facturas", params={"empresa_id": ajena}).status_code == 404
    assert _radicar(analista, ajena).status_code == 404


def test_ti_solo_lectura(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TESORERIA_DOCUMENTOS_DIR", str(tmp_path))
    empresa_id = crear_empresa("Tesorería TI")
    ti, _ = cliente_con_rol(ROL_TI)
    assert ti.get("/api/v1/tesoreria/facturas", params={"empresa_id": empresa_id}).status_code == 200
    assert _radicar(ti, empresa_id).status_code == 403
