import os
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.empresas import Empresa
from app.main import app
from app.motores.cartera_ocs.comprobantes import radicar_comprobante
from app.motores.cartera_ocs.financiacion import (
    OperacionFinanciada,
    generar_condicion_pago,
)
from app.motores.cartera_ocs.persistencia import guardar_comprobante


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def test_web_returns_pending_proof_inbox() -> None:
    engine = _engine()
    with Session(engine) as session:
        empresa = Empresa(nombre="Empresa bandeja web")
        session.add(empresa)
        session.flush()
        empresa_id = empresa.id

        condicion = generar_condicion_pago(
            OperacionFinanciada(
                oc="OC-INBOX",
                cliente="Cliente Inbox",
                pais="COLOMBIA",
                valor_ddp=2000,
                tipo_negociacion="50% anticipo / 50% a la entrega",
                fecha_entrega=date(2026, 9, 28),
                comercial="COMERCIAL INBOX",
            )
        )
        guardar_comprobante(
            session,
            empresa_id=empresa_id,
            comprobante=radicar_comprobante(
                condicion=condicion,
                nombre_archivo="inbox.pdf",
                contenido=b"inbox",
            ),
            ubicacion_archivo="inbox/path.pdf",
        )
        session.commit()

    response = TestClient(app).get(
        f"/cartera/comprobantes/pendientes?empresa_id={empresa_id}"
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["oc"] == "OC-INBOX"
    assert body[0]["cliente"] == "Cliente Inbox"
    assert body[0]["estado_auditoria"] == "PENDIENTE"
    assert body[0]["nombre_archivo"] == "inbox.pdf"
    assert body[0]["monto_esperado"] == 1000.0
    assert "ubicacion_archivo" not in body[0]
