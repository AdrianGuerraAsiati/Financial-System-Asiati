import os
from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.cargas import Carga
from app.core.cargas.errors import ContextoCargaInvalidoError
from app.core.cargas.service import registrar_carga
from app.core.empresas import Empresa
from app.core.fuentes import Fuente
from app.core.periodos import Periodo


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def test_load_registration_rejects_cross_empresa_context() -> None:
    engine = _engine()

    with Session(engine) as session:
        empresa_a = Empresa(nombre="Empresa carga A")
        empresa_b = Empresa(nombre="Empresa carga B")
        session.add_all([empresa_a, empresa_b])
        session.flush()

        fuente_b = Fuente(
            empresa_id=empresa_b.id,
            nombre="Fuente empresa B",
        )
        periodo_a = Periodo(
            empresa_id=empresa_a.id,
            fecha_inicio=date(2027, 1, 1),
            fecha_fin=date(2027, 1, 31),
        )
        session.add_all([fuente_b, periodo_a])
        session.flush()

        with pytest.raises(ContextoCargaInvalidoError):
            registrar_carga(
                session,
                empresa_id=empresa_a.id,
                fuente_id=fuente_b.id,
                periodo_id=periodo_a.id,
                contenido_hash="d" * 64,
            )

        assert session.scalar(
            select(Carga).where(Carga.contenido_hash == "d" * 64)
        ) is None
        session.rollback()


def test_load_registration_persists_consistent_context() -> None:
    engine = _engine()

    with Session(engine) as session:
        empresa = Empresa(nombre="Empresa carga consistente")
        session.add(empresa)
        session.flush()

        fuente = Fuente(
            empresa_id=empresa.id,
            nombre="Fuente consistente",
        )
        periodo = Periodo(
            empresa_id=empresa.id,
            fecha_inicio=date(2027, 2, 1),
            fecha_fin=date(2027, 2, 28),
        )
        session.add_all([fuente, periodo])
        session.flush()

        empresa_id = empresa.id
        fuente_id = fuente.id
        periodo_id = periodo.id

        carga = registrar_carga(
            session,
            empresa_id=empresa_id,
            fuente_id=fuente_id,
            periodo_id=periodo_id,
            contenido_hash="e" * 64,
        )
        session.commit()
        carga_id = carga.id

    with Session(engine) as session:
        persisted = session.get(Carga, carga_id)

        assert persisted is not None
        assert persisted.empresa_id == empresa_id
        assert persisted.fuente_id == fuente_id
        assert persisted.periodo_id == periodo_id
