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


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def _empresa_id() -> int:
    with Session(_engine()) as session:
        empresa = Empresa(nombre="ASIATI guardrails")
        session.add(empresa)
        session.commit()
        return empresa.id


def _data(empresa_id: int) -> dict[str, str]:
    return {
        "empresa_id": str(empresa_id),
        "oc": "OC-GUARD",
        "cliente": "Cliente Guard",
        "pais": "COLOMBIA",
        "valor_ddp": "10000",
        "tipo_negociacion": "50% anticipo / 50% pago a 30 días",
        "fecha_entrega": date(2026, 9, 10).isoformat(),
        "comercial": "COMERCIAL A",
    }


def test_upload_rejects_unsupported_content_type(tmp_path: Path) -> None:
    empresa_id = _empresa_id()
    app.dependency_overrides[obtener_almacen_comprobantes] = (
        lambda: AlmacenLocalComprobantes(tmp_path)
    )
    try:
        response = cliente_superadmin().post(
            "/api/v1/cartera/comprobantes",
            data=_data(empresa_id),
            files={"archivo": ("soporte.txt", b"texto", "text/plain")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 415


def test_upload_rejects_file_above_configured_limit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("CARTERA_COMPROBANTES_MAX_BYTES", "4")
    empresa_id = _empresa_id()
    app.dependency_overrides[obtener_almacen_comprobantes] = (
        lambda: AlmacenLocalComprobantes(tmp_path)
    )
    try:
        response = cliente_superadmin().post(
            "/api/v1/cartera/comprobantes",
            data=_data(empresa_id),
            files={"archivo": ("soporte.pdf", b"12345", "application/pdf")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 413


def test_upload_rejects_duplicate_content_for_same_empresa(tmp_path: Path) -> None:
    empresa_id = _empresa_id()
    app.dependency_overrides[obtener_almacen_comprobantes] = (
        lambda: AlmacenLocalComprobantes(tmp_path)
    )
    client = cliente_superadmin()

    try:
        primero = client.post(
            "/api/v1/cartera/comprobantes",
            data=_data(empresa_id),
            files={"archivo": ("uno.pdf", b"mismo soporte", "application/pdf")},
        )
        segundo = client.post(
            "/api/v1/cartera/comprobantes",
            data={**_data(empresa_id), "oc": "OC-GUARD-2"},
            files={"archivo": ("dos.pdf", b"mismo soporte", "application/pdf")},
        )
    finally:
        app.dependency_overrides.clear()

    assert primero.status_code == 201
    assert segundo.status_code == 409


def test_upload_response_does_not_expose_internal_storage_path(tmp_path: Path) -> None:
    empresa_id = _empresa_id()
    app.dependency_overrides[obtener_almacen_comprobantes] = (
        lambda: AlmacenLocalComprobantes(tmp_path)
    )
    try:
        response = cliente_superadmin().post(
            "/api/v1/cartera/comprobantes",
            data={**_data(empresa_id), "oc": "OC-SAFE"},
            files={"archivo": ("safe.pdf", b"soporte seguro", "application/pdf")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert "ubicacion_archivo" not in response.json()
