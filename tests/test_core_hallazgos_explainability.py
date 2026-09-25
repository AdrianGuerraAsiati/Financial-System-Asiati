import os
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.empresas import Empresa
from app.core.hallazgos import Hallazgo
from app.core.hallazgos.creation import registrar_hallazgo_motor
from app.core.periodos import Periodo


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def test_explainable_finding_roundtrips_structured_evidence() -> None:
    engine = _engine()

    with Session(engine) as session:
        empresa = Empresa(nombre="Empresa hallazgo explicable")
        session.add(empresa)
        session.flush()

        periodo = Periodo(
            empresa_id=empresa.id,
            fecha_inicio=date(2027, 3, 1),
            fecha_fin=date(2027, 3, 31),
        )
        session.add(periodo)
        session.flush()

        hallazgo = registrar_hallazgo_motor(
            session,
            periodo_id=periodo.id,
            motor_slug="conciliacion_wallets",
            codigo_regla="wallet_pago_no_encontrado",
            descripcion="No se encontró un pago conciliable para la orden.",
            evidencia={
                "orden_id": "OC-456",
                "valor": 7300000,
                "matches": 0,
            },
            critico=True,
        )
        session.commit()
        hallazgo_id = hallazgo.id

    with Session(engine) as session:
        persisted = session.get(Hallazgo, hallazgo_id)

        assert persisted is not None
        assert persisted.motor_slug == "conciliacion_wallets"
        assert persisted.codigo_regla == "wallet_pago_no_encontrado"
        assert persisted.descripcion == "No se encontró un pago conciliable para la orden."
        assert persisted.evidencia == {
            "orden_id": "OC-456",
            "valor": 7300000,
            "matches": 0,
        }
        assert persisted.critico is True
        assert persisted.resuelto is False
