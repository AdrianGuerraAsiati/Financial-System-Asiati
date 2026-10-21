"""Radicación rápida de comprobantes sin inferir montos ni asociación bancaria."""
import os
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.empresas import Empresa
from app.main import app
from app.motores.cartera_ocs.persistencia import ComprobantePagoPersistido
from app.motores.cartera_ocs.api import obtener_almacen_comprobantes
from app.motores.cartera_ocs.almacenamiento import AlmacenLocalComprobantes
from tests.apoyo_auth import cliente_superadmin


def _empresa() -> int:
    engine = create_engine(os.environ["DATABASE_URL"])
    with Session(engine) as session:
        empresa = Empresa(nombre="Prueba comprobante simple")
        session.add(empresa)
        session.commit()
        return empresa.id


def test_radicacion_simple_conserva_estado_e_importes_desconocidos(tmp_path: Path) -> None:
    empresa = _empresa()
    app.dependency_overrides[obtener_almacen_comprobantes] = (
        lambda: AlmacenLocalComprobantes(tmp_path)
    )
    client = cliente_superadmin()
    try:
        respuesta = client.post(
            "/api/v1/cartera/comprobantes",
            data={"empresa_id": str(empresa), "oc": "  OC-RAPIDA  "},
            files={"archivo": ("pago.pdf", b"contenido de soporte", "application/pdf")},
        )
        assert respuesta.status_code == 201, respuesta.text
        payload = respuesta.json()
        assert payload["estado_auditoria"] == "PENDIENTE_ASOCIACION"
        assert payload["oc"] == "OC-RAPIDA"
        assert payload["monto_esperado"] is None
        assert "ubicacion_archivo" not in payload

        bandeja = client.get("/api/v1/cartera/comprobantes/pendientes", params={"empresa_id": empresa})
        assert bandeja.status_code == 200, bandeja.text
        item = next(x for x in bandeja.json() if x["id"] == payload["id"])
        assert item["monto_esperado"] is None
        assert item["comercial"] is None
        assert item["estado_auditoria"] == "PENDIENTE_ASOCIACION"
        assert "nombre_archivo" in item

        motor = create_engine(os.environ["DATABASE_URL"])
        with Session(motor) as session:
            registro = session.get(ComprobantePagoPersistido, payload["id"])
            assert registro is not None
            assert registro.cliente is None
            assert registro.pais is None
            assert registro.comercial is None
            assert registro.monto_esperado is None
        guardado = list(tmp_path.rglob("*.pdf"))
        assert len(guardado) == 1
        assert guardado[0].read_bytes() == b"contenido de soporte"
    finally:
        app.dependency_overrides.clear()


def test_radicacion_rechaza_datos_financieros_parciales(tmp_path: Path) -> None:
    empresa = _empresa()
    app.dependency_overrides[obtener_almacen_comprobantes] = (
        lambda: AlmacenLocalComprobantes(tmp_path)
    )
    try:
        respuesta = cliente_superadmin().post(
            "/api/v1/cartera/comprobantes",
            data={"empresa_id": str(empresa), "oc": "OC-PARCIAL", "cliente": "Cliente A"},
            files={"archivo": ("soporte.pdf", b"contenido", "application/pdf")},
        )
        assert respuesta.status_code == 422
        assert not list(tmp_path.rglob("*.pdf"))
    finally:
        app.dependency_overrides.clear()


def test_radicacion_simple_sigue_rechazando_duplicados(tmp_path: Path) -> None:
    empresa = _empresa()
    app.dependency_overrides[obtener_almacen_comprobantes] = (
        lambda: AlmacenLocalComprobantes(tmp_path)
    )
    client = cliente_superadmin()
    try:
        kw = dict(
            data={"empresa_id": str(empresa), "oc": "OC-RAPIDA"},
            files={"archivo": ("soporte.pdf", b"mismo archivo", "application/pdf")},
        )
        assert client.post("/api/v1/cartera/comprobantes", **kw).status_code == 201
        second = client.post(
            "/api/v1/cartera/comprobantes",
            data={"empresa_id": str(empresa), "oc": "OC-RAPIDA-DOS"},
            files={"archivo": ("soporte.pdf", b"mismo archivo", "application/pdf")},
        )
        assert second.status_code == 409
    finally:
        app.dependency_overrides.clear()


def test_pagina_muestra_modo_rapido_y_completo():
    from fastapi.testclient import TestClient
    html = TestClient(app).get("/").text
    assert 'id="form-comprobante"' in html
    assert 'name="oc" maxlength="120"' in html
    assert 'id="cartera-comprobante-avanzado"' in html
    assert 'id="cartera-comprobante-datos"' in html
    assert 'name="archivo" type="file"' in html
    js = TestClient(app).get("/static/app.js").text
    assert "comprobanteExtras.disabled = !comprobanteAvanzado.open" in js
    assert "PENDIENTE_ASOCIACION" in js
