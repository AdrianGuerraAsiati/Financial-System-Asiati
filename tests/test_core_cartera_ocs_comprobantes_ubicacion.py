import os
from datetime import date

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


def test_payment_proof_storage_location_is_persisted() -> None:
    condicion = generar_condicion_pago(
        OperacionFinanciada(
            oc="OC-789",
            cliente="Cliente Storage",
            pais="COLOMBIA",
            valor_ddp=2000,
            tipo_negociacion="50% anticipo / 50% a la entrega",
            fecha_entrega=date(2026, 9, 28),
            comercial="COMERCIAL A",
        )
    )
    comprobante = radicar_comprobante(
        condicion=condicion,
        nombre_archivo="pago.pdf",
        contenido=b"pago",
    )

    engine = _engine()
    with Session(engine) as session:
        empresa = Empresa(nombre="ASIATI storage")
        session.add(empresa)
        session.flush()

        registro = guardar_comprobante(
            session,
            empresa_id=empresa.id,
            comprobante=comprobante,
            ubicacion_archivo="1/OC-789/hash-pago.pdf",
        )
        session.commit()
        registro_id = registro.id

    with Session(engine) as session:
        persisted = session.get(ComprobantePagoPersistido, registro_id)

        assert persisted is not None
        assert persisted.ubicacion_archivo == "1/OC-789/hash-pago.pdf"
