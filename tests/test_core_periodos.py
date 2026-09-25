import os
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.empresas import Empresa
from app.core.periodos import Periodo


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def test_periodo_belongs_to_empresa() -> None:
    engine = _engine()

    with Session(engine) as session:
        empresa = Empresa(nombre="Empresa periodos")
        session.add(empresa)
        session.flush()

        periodo = Periodo(
            empresa_id=empresa.id,
            fecha_inicio=date(2026, 9, 1),
            fecha_fin=date(2026, 9, 30),
        )
        session.add(periodo)
        session.flush()

        assert periodo.empresa_id == empresa.id
        session.rollback()


def test_same_period_cannot_be_registered_twice_for_same_empresa() -> None:
    engine = _engine()

    with Session(engine) as session:
        empresa = Empresa(nombre="Empresa periodo unico")
        session.add(empresa)
        session.flush()

        session.add(
            Periodo(
                empresa_id=empresa.id,
                fecha_inicio=date(2026, 9, 1),
                fecha_fin=date(2026, 9, 30),
            )
        )
        session.flush()

        session.add(
            Periodo(
                empresa_id=empresa.id,
                fecha_inicio=date(2026, 9, 1),
                fecha_fin=date(2026, 9, 30),
            )
        )

        with pytest.raises(IntegrityError):
            session.flush()

        session.rollback()


def test_same_period_can_exist_for_different_empresas() -> None:
    engine = _engine()

    with Session(engine) as session:
        empresa_a = Empresa(nombre="Empresa periodo A")
        empresa_b = Empresa(nombre="Empresa periodo B")
        session.add_all([empresa_a, empresa_b])
        session.flush()

        session.add_all(
            [
                Periodo(
                    empresa_id=empresa_a.id,
                    fecha_inicio=date(2026, 9, 1),
                    fecha_fin=date(2026, 9, 30),
                ),
                Periodo(
                    empresa_id=empresa_b.id,
                    fecha_inicio=date(2026, 9, 1),
                    fecha_fin=date(2026, 9, 30),
                ),
            ]
        )

        session.flush()
        session.rollback()
