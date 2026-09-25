import os
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.cargas import Carga
from app.core.empresas import Empresa
from app.core.fuentes import Fuente
from app.core.periodos import Periodo


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def _contexto_carga(session: Session, empresa: Empresa) -> tuple[Fuente, Periodo]:
    fuente = Fuente(empresa_id=empresa.id, nombre=f"Fuente {empresa.nombre}")
    periodo = Periodo(
        empresa_id=empresa.id,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 1, 31),
    )
    session.add_all([fuente, periodo])
    session.flush()
    return fuente, periodo


def test_same_content_hash_cannot_be_registered_twice_for_same_empresa() -> None:
    engine = _engine()

    with Session(engine) as session:
        empresa = Empresa(nombre="Empresa idempotencia")
        session.add(empresa)
        session.flush()
        fuente, periodo = _contexto_carga(session, empresa)

        session.add(
            Carga(
                empresa_id=empresa.id,
                fuente_id=fuente.id,
                periodo_id=periodo.id,
                contenido_hash="a" * 64,
            )
        )
        session.flush()

        session.add(
            Carga(
                empresa_id=empresa.id,
                fuente_id=fuente.id,
                periodo_id=periodo.id,
                contenido_hash="a" * 64,
            )
        )

        with pytest.raises(IntegrityError):
            session.flush()

        session.rollback()


def test_same_content_hash_can_exist_for_different_empresas() -> None:
    engine = _engine()

    with Session(engine) as session:
        empresa_a = Empresa(nombre="Empresa A")
        empresa_b = Empresa(nombre="Empresa B")
        session.add_all([empresa_a, empresa_b])
        session.flush()

        fuente_a, periodo_a = _contexto_carga(session, empresa_a)
        fuente_b, periodo_b = _contexto_carga(session, empresa_b)

        session.add_all(
            [
                Carga(
                    empresa_id=empresa_a.id,
                    fuente_id=fuente_a.id,
                    periodo_id=periodo_a.id,
                    contenido_hash="b" * 64,
                ),
                Carga(
                    empresa_id=empresa_b.id,
                    fuente_id=fuente_b.id,
                    periodo_id=periodo_b.id,
                    contenido_hash="b" * 64,
                ),
            ]
        )

        session.flush()
        session.rollback()
