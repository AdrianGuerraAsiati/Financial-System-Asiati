import os
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.empresas import Empresa
from app.core.hallazgos import Hallazgo
from app.core.motor import Resultado
from app.core.periodos import Periodo
from app.motores.conciliacion_wallets.hallazgos import registrar_resultado


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def test_wallet_result_persists_as_explainable_finding() -> None:
    engine = _engine()

    with Session(engine) as session:
        empresa = Empresa(nombre="Empresa resultado wallets")
        session.add(empresa)
        session.flush()

        periodo = Periodo(
            empresa_id=empresa.id,
            fecha_inicio=date(2027, 4, 1),
            fecha_fin=date(2027, 4, 30),
        )
        session.add(periodo)
        session.flush()

        resultado = Resultado(
            codigo="wallet_pago_no_encontrado",
            estado="requiere_revision",
            datos={
                "orden_id": "OC-456",
                "valor": 7300000,
                "matches": 0,
            },
            descripcion="No se encontró un pago conciliable para la orden.",
            critico=True,
        )

        hallazgo = registrar_resultado(
            session,
            periodo_id=periodo.id,
            resultado=resultado,
        )
        session.commit()
        hallazgo_id = hallazgo.id

    with Session(engine) as session:
        persisted = session.get(Hallazgo, hallazgo_id)

        assert persisted is not None
        assert persisted.motor_slug == "conciliacion_wallets"
        assert persisted.codigo_regla == "wallet_pago_no_encontrado"
        assert persisted.descripcion == "No se encontró un pago conciliable para la orden."
        assert persisted.evidencia["orden_id"] == "OC-456"
        assert persisted.critico is True
