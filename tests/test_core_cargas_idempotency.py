import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.cargas import Carga
from app.core.empresas import Empresa


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def test_same_content_hash_cannot_be_registered_twice_for_same_empresa() -> None:
    engine = _engine()

    with Session(engine) as session:
        empresa = Empresa(nombre="Empresa idempotencia")
        session.add(empresa)
        session.flush()

        session.add(
            Carga(
                empresa_id=empresa.id,
                contenido_hash="a" * 64,
            )
        )
        session.flush()

        session.add(
            Carga(
                empresa_id=empresa.id,
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

        session.add_all(
            [
                Carga(empresa_id=empresa_a.id, contenido_hash="b" * 64),
                Carga(empresa_id=empresa_b.id, contenido_hash="b" * 64),
            ]
        )

        session.flush()
        session.rollback()
