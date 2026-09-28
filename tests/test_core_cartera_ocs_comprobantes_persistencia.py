import os
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.empresas import Empresa
from app.motores.cartera_ocs.comprobantes import radicar_comprobante
from app.motores.cartera_ocs.financiacion import (
    OperacionFinanciada,
    generar_condicion_pago,
)
from app.motores.cartera_ocs.persistencia import (
    ComprobantePagoPersistido,
    guardar_comprobante,
)


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def _comprobante():
    condicion = generar_condicion_pago(
        OperacionFinanciada(
            oc="OC-123",
            cliente="Cliente A",
            pais="COLOMBIA",
            valor_ddp=10000,
            tipo_negociacion="50% anticipo / 50% pago a 30 días",
            fecha_entrega=date(2026, 9, 10),
            comercial="COMERCIAL A",
        )
    )
    return radicar_comprobante(
        condicion=condicion,
        nombre_archivo="comprobante.pdf",
        contenido=b"contenido comprobante",
    )


def test_comprobante_pendiente_persists_with_business_context() -> None:
    engine = _engine()

    with Session(engine) as session:
        empresa = Empresa(nombre="ASIATI Comercial comprobantes")
        session.add(empresa)
        session.flush()
        empresa_id = empresa.id

        registro = guardar_comprobante(
            session,
            empresa_id=empresa_id,
            comprobante=_comprobante(),
        )
        session.commit()
        registro_id = registro.id

    with Session(engine) as session:
        persisted = session.get(ComprobantePagoPersistido, registro_id)

        assert persisted is not None
        assert persisted.empresa_id == empresa_id
        assert persisted.oc == "OC-123"
        assert persisted.cliente == "Cliente A"
        assert persisted.pais == "COLOMBIA"
        assert persisted.comercial == "COMERCIAL A"
        assert persisted.monto_esperado == Decimal("5000.00")
        assert persisted.nombre_archivo == "comprobante.pdf"
        assert len(persisted.contenido_hash) == 64
        assert persisted.estado_auditoria == "PENDIENTE"
        assert persisted.creado_en is not None
