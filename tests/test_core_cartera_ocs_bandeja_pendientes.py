import os
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.empresas import Empresa
from app.motores.cartera_ocs.bandeja import listar_comprobantes_pendientes
from app.motores.cartera_ocs.comprobantes import radicar_comprobante
from app.motores.cartera_ocs.financiacion import (
    OperacionFinanciada,
    generar_condicion_pago,
)
from app.motores.cartera_ocs.persistencia import guardar_comprobante


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def _comprobante(oc: str):
    condicion = generar_condicion_pago(
        OperacionFinanciada(
            oc=oc,
            cliente=f"Cliente {oc}",
            pais="COLOMBIA",
            valor_ddp=1000,
            tipo_negociacion="50% anticipo / 50% a la entrega",
            fecha_entrega=date(2026, 9, 28),
            comercial="COMERCIAL A",
        )
    )
    return radicar_comprobante(
        condicion=condicion,
        nombre_archivo=f"{oc}.pdf",
        contenido=oc.encode(),
    )


def test_pending_inbox_filters_by_empresa_and_status() -> None:
    engine = _engine()

    with Session(engine) as session:
        empresa_a = Empresa(nombre="Empresa bandeja A")
        empresa_b = Empresa(nombre="Empresa bandeja B")
        session.add_all([empresa_a, empresa_b])
        session.flush()
        empresa_a_id = empresa_a.id

        pendiente = guardar_comprobante(
            session,
            empresa_id=empresa_a.id,
            comprobante=_comprobante("OC-PEND"),
            ubicacion_archivo="a/pend.pdf",
        )
        aprobado = guardar_comprobante(
            session,
            empresa_id=empresa_a.id,
            comprobante=_comprobante("OC-OK"),
            ubicacion_archivo="a/ok.pdf",
        )
        aprobado.estado_auditoria = "APROBADO"

        guardar_comprobante(
            session,
            empresa_id=empresa_b.id,
            comprobante=_comprobante("OC-OTRA"),
            ubicacion_archivo="b/otra.pdf",
        )
        session.commit()

    with Session(engine) as session:
        pendientes = listar_comprobantes_pendientes(
            session,
            empresa_id=empresa_a_id,
        )

        assert [item.oc for item in pendientes] == ["OC-PEND"]
        assert pendientes[0].estado_auditoria == "PENDIENTE"
        assert pendientes[0].cliente == "Cliente OC-PEND"
        assert pendientes[0].nombre_archivo == "OC-PEND.pdf"
