import os
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.empresas import Empresa
from app.main import app
from tests.apoyo_auth import cliente_superadmin
from app.motores.cartera_ocs.api import obtener_almacen_comprobantes
from app.motores.cartera_ocs.almacenamiento import AlmacenLocalComprobantes
from app.motores.cartera_ocs.comprobantes import radicar_comprobante
from app.motores.cartera_ocs.financiacion import (
    OperacionFinanciada,
    generar_condicion_pago,
)
from app.motores.cartera_ocs.persistencia import guardar_comprobante


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def _crear_comprobante(tmp_path: Path) -> tuple[int, int, int]:
    almacen = AlmacenLocalComprobantes(tmp_path)
    condicion = generar_condicion_pago(
        OperacionFinanciada(
            oc="OC-VIEW",
            cliente="Cliente View",
            pais="COLOMBIA",
            valor_ddp=1000,
            tipo_negociacion="50% anticipo / 50% a la entrega",
            fecha_entrega=date(2026, 9, 28),
            comercial="COMERCIAL VIEW",
        )
    )
    comprobante = radicar_comprobante(
        condicion=condicion,
        nombre_archivo="soporte-view.pdf",
        contenido=b"%PDF-soporte",
    )

    with Session(_engine()) as session:
        empresa = Empresa(nombre="Empresa soporte view")
        otra_empresa = Empresa(nombre="Otra empresa soporte view")
        session.add_all([empresa, otra_empresa])
        session.flush()

        ubicacion = almacen.guardar(
            empresa_id=empresa.id,
            oc=comprobante.oc,
            nombre_archivo=comprobante.nombre_archivo,
            contenido_hash=comprobante.contenido_hash,
            contenido=b"%PDF-soporte",
        )
        registro = guardar_comprobante(
            session,
            empresa_id=empresa.id,
            comprobante=comprobante,
            ubicacion_archivo=ubicacion,
        )
        session.commit()
        return registro.id, empresa.id, otra_empresa.id


def test_web_serves_payment_proof_without_exposing_storage_path(tmp_path: Path) -> None:
    comprobante_id, empresa_id, _ = _crear_comprobante(tmp_path)
    app.dependency_overrides[obtener_almacen_comprobantes] = (
        lambda: AlmacenLocalComprobantes(tmp_path)
    )
    try:
        response = cliente_superadmin().get(
            f"/api/v1/cartera/comprobantes/{comprobante_id}/archivo?empresa_id={empresa_id}"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.content == b"%PDF-soporte"
    assert response.headers["content-type"].startswith("application/pdf")
    assert "soporte-view.pdf" in response.headers["content-disposition"]
    assert str(tmp_path) not in response.text


def test_web_does_not_serve_proof_from_another_company(tmp_path: Path) -> None:
    comprobante_id, _, otra_empresa_id = _crear_comprobante(tmp_path)
    app.dependency_overrides[obtener_almacen_comprobantes] = (
        lambda: AlmacenLocalComprobantes(tmp_path)
    )
    try:
        response = cliente_superadmin().get(
            f"/api/v1/cartera/comprobantes/{comprobante_id}/archivo"
            f"?empresa_id={otra_empresa_id}"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
