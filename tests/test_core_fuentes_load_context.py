import os
from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.cargas import Carga
from app.core.empresas import Empresa
from app.core.fuentes import Fuente
from app.core.periodos import Periodo


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def test_source_belongs_to_empresa_and_load_keeps_source_period_context() -> None:
    engine = _engine()

    with Session(engine) as session:
        empresa = Empresa(nombre="Empresa fuentes")
        session.add(empresa)
        session.flush()

        fuente = Fuente(
            empresa_id=empresa.id,
            nombre="Wallet principal",
        )
        session.add(fuente)

        periodo = Periodo(
            empresa_id=empresa.id,
            fecha_inicio=date(2026, 12, 1),
            fecha_fin=date(2026, 12, 31),
        )
        session.add(periodo)
        session.flush()

        carga = Carga(
            empresa_id=empresa.id,
            fuente_id=fuente.id,
            periodo_id=periodo.id,
            contenido_hash="c" * 64,
        )
        session.add(carga)
        session.commit()

        carga_id = carga.id
        fuente_id = fuente.id
        periodo_id = periodo.id
        empresa_id = empresa.id

    with Session(engine) as session:
        persisted_fuente = session.get(Fuente, fuente_id)
        persisted_carga = session.scalar(
            select(Carga).where(Carga.id == carga_id)
        )

        assert persisted_fuente is not None
        assert persisted_fuente.empresa_id == empresa_id
        assert persisted_fuente.nombre == "Wallet principal"

        assert persisted_carga is not None
        assert persisted_carga.fuente_id == fuente_id
        assert persisted_carga.periodo_id == periodo_id
