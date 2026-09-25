import os
from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.empresas import Empresa
from app.core.hallazgos import Hallazgo
from app.core.periodos import Periodo


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def test_hallazgo_belongs_to_period_and_persists_state() -> None:
    engine = _engine()

    with Session(engine) as session:
        empresa = Empresa(nombre="Empresa hallazgos")
        session.add(empresa)
        session.flush()

        periodo = Periodo(
            empresa_id=empresa.id,
            fecha_inicio=date(2026, 9, 1),
            fecha_fin=date(2026, 9, 30),
        )
        session.add(periodo)
        session.flush()
        periodo_id = periodo.id

        hallazgo = Hallazgo(
            periodo_id=periodo_id,
            critico=True,
            resuelto=False,
        )
        session.add(hallazgo)
        session.commit()
        hallazgo_id = hallazgo.id

    with Session(engine) as session:
        persisted = session.scalar(
            select(Hallazgo).where(Hallazgo.id == hallazgo_id)
        )

        assert persisted is not None
        assert persisted.periodo_id == periodo_id
        assert persisted.critico is True
        assert persisted.resuelto is False
