import os
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.cargas import calcular_hash_contenido, registrar_carga_desde_contenido
from app.core.empresas import Empresa
from app.core.fuentes import Fuente
from app.core.periodos import Periodo


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def _contexto(session: Session) -> tuple[Empresa, Fuente, Periodo]:
    empresa = Empresa(nombre="Empresa carga desde contenido")
    session.add(empresa)
    session.flush()

    fuente = Fuente(empresa_id=empresa.id, nombre="Archivo operativo")
    periodo = Periodo(
        empresa_id=empresa.id,
        fecha_inicio=date(2026, 9, 1),
        fecha_fin=date(2026, 9, 30),
    )
    session.add_all([fuente, periodo])
    session.flush()
    return empresa, fuente, periodo


def test_file_content_is_registered_with_its_deterministic_hash() -> None:
    engine = _engine()
    contenido = b"orden_id,valor\nOC-1,1000\n"

    with Session(engine) as session:
        empresa, fuente, periodo = _contexto(session)

        carga = registrar_carga_desde_contenido(
            session,
            empresa_id=empresa.id,
            fuente_id=fuente.id,
            periodo_id=periodo.id,
            contenido=contenido,
        )
        session.flush()

        assert carga.contenido_hash == calcular_hash_contenido(contenido)
        assert carga.empresa_id == empresa.id
        assert carga.fuente_id == fuente.id
        assert carga.periodo_id == periodo.id

        session.rollback()


def test_same_file_content_remains_idempotent_for_same_empresa() -> None:
    engine = _engine()
    contenido = b"mismo archivo"

    with Session(engine) as session:
        empresa, fuente, periodo = _contexto(session)

        registrar_carga_desde_contenido(
            session,
            empresa_id=empresa.id,
            fuente_id=fuente.id,
            periodo_id=periodo.id,
            contenido=contenido,
        )
        session.flush()

        registrar_carga_desde_contenido(
            session,
            empresa_id=empresa.id,
            fuente_id=fuente.id,
            periodo_id=periodo.id,
            contenido=contenido,
        )

        with pytest.raises(IntegrityError):
            session.flush()

        session.rollback()
