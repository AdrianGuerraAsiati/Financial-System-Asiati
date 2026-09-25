import os
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.empresas import Empresa
from app.core.periodos import Periodo
from app.core.periodos.service import cerrar_periodo


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def test_new_period_starts_open() -> None:
    engine = _engine()

    with Session(engine) as session:
        empresa = Empresa(nombre="Empresa cierre inicial")
        session.add(empresa)
        session.flush()

        periodo = Periodo(
            empresa_id=empresa.id,
            fecha_inicio=date(2026, 9, 1),
            fecha_fin=date(2026, 9, 30),
        )
        session.add(periodo)
        session.flush()

        assert periodo.cerrado is False
        session.rollback()


def test_period_can_be_closed_and_persisted() -> None:
    engine = _engine()

    with Session(engine) as session:
        empresa = Empresa(nombre="Empresa cierre persistente")
        session.add(empresa)
        session.flush()

        periodo = Periodo(
            empresa_id=empresa.id,
            fecha_inicio=date(2026, 10, 1),
            fecha_fin=date(2026, 10, 31),
        )
        session.add(periodo)
        session.flush()

        cerrar_periodo(
            session,
            periodo,
            actor="sistemas@asiati.com.co",
            motivo="Cierre mensual",
        )
        periodo_id = periodo.id
        session.commit()

    with Session(engine) as session:
        persisted = session.get(Periodo, periodo_id)

        assert persisted is not None
        assert persisted.cerrado is True
