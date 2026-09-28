import os
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.empresas import Empresa
from app.main import app
from app.motores.cartera_ocs.persistencia import ComprobantePagoPersistido


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def test_web_upload_radicates_and_stores_payment_proof(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CARTERA_COMPROBANTES_DIR", str(tmp_path))

    engine = _engine()
    with Session(engine) as session:
        empresa = Empresa(nombre="ASIATI web upload")
        session.add(empresa)
        session.commit()
        empresa_id = empresa.id

    client = TestClient(app)
    response = client.post(
        "/cartera/comprobantes",
        data={
            "empresa_id": str(empresa_id),
            "oc": "OC-WEB-1",
            "cliente": "Cliente Web",
            "pais": "COLOMBIA",
            "valor_ddp": "10000",
            "tipo_negociacion": "50% anticipo / 50% pago a 30 días",
            "fecha_entrega": "2026-09-10",
            "comercial": "COMERCIAL WEB",
        },
        files={
            "archivo": (
                "comprobante web.pdf",
                b"contenido comprobante web",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["oc"] == "OC-WEB-1"
    assert body["estado_auditoria"] == "PENDIENTE"
    assert body["monto_esperado"] == 5000.0
    assert body["ubicacion_archivo"]

    assert (tmp_path / body["ubicacion_archivo"]).read_bytes() == b"contenido comprobante web"

    with Session(engine) as session:
        persisted = session.get(ComprobantePagoPersistido, body["id"])

        assert persisted is not None
        assert persisted.empresa_id == empresa_id
        assert persisted.oc == "OC-WEB-1"
        assert persisted.estado_auditoria == "PENDIENTE"
        assert persisted.ubicacion_archivo == body["ubicacion_archivo"]
