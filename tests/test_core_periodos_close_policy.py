import os
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.empresas import Empresa
from app.core.hallazgos import Hallazgo
from app.core.periodos import Periodo
from app.core.periodos.errors import HallazgosCriticosAbiertosError
from app.core.periodos.service import cerrar_periodo


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def test_open_critical_finding_blocks_period_close_until_resolved() -> None:
    engine = _engine()

    with Session(engine) as session:
        empresa = Empresa(nombre="Empresa bloqueo cierre")
        session.add(empresa)
        session.flush()

        periodo = Periodo(
            empresa_id=empresa.id,
            fecha_inicio=date(2026, 11, 1),
            fecha_fin=date(2026, 11, 30),
        )
        session.add(periodo)
        session.flush()

        hallazgo = Hallazgo(
            periodo_id=periodo.id,
            critico=True,
            resuelto=False,
        )
        session.add(hallazgo)
        session.flush()

        with pytest.raises(HallazgosCriticosAbiertosError):
            cerrar_periodo(
                session,
                periodo,
                actor="sistemas@asiati.com.co",
                motivo="Intento con crítico abierto",
            )

        assert periodo.cerrado is False

        hallazgo.resuelto = True
        session.flush()

        cerrar_periodo(
            session,
            periodo,
            actor="sistemas@asiati.com.co",
            motivo="Críticos resueltos",
        )

        assert periodo.cerrado is True
        session.rollback()
