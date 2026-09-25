import os
from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.empresas import Empresa
from app.core.periodos import Periodo
from app.core.periodos.history import PeriodoCierreEvento
from app.core.periodos.service import cerrar_periodo, reabrir_periodo


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def test_close_and_reopen_history_is_persisted_in_order() -> None:
    engine = _engine()

    with Session(engine) as session:
        empresa = Empresa(nombre="Empresa historial cierres")
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

        cerrar_periodo(
            session,
            periodo,
            actor="sistemas@asiati.com.co",
            motivo="Cierre mensual",
        )
        session.commit()

    with Session(engine) as session:
        periodo = session.get(Periodo, periodo_id)
        assert periodo is not None

        reabrir_periodo(
            session,
            periodo,
            actor="direccion@asiati.com.co",
            motivo="Ajuste autorizado",
        )
        session.commit()

    with Session(engine) as session:
        eventos = list(
            session.scalars(
                select(PeriodoCierreEvento)
                .where(PeriodoCierreEvento.periodo_id == periodo_id)
                .order_by(PeriodoCierreEvento.id)
            )
        )

        assert [evento.accion for evento in eventos] == ["CERRAR", "REABRIR"]
        assert eventos[0].actor == "sistemas@asiati.com.co"
        assert eventos[1].actor == "direccion@asiati.com.co"
        assert eventos[1].motivo == "Ajuste autorizado"
        assert all(evento.ocurrido_en is not None for evento in eventos)


def test_close_state_and_history_rollback_together() -> None:
    engine = _engine()

    with Session(engine) as session:
        empresa = Empresa(nombre="Empresa rollback cierre")
        session.add(empresa)
        session.flush()

        periodo = Periodo(
            empresa_id=empresa.id,
            fecha_inicio=date(2026, 10, 1),
            fecha_fin=date(2026, 10, 31),
        )
        session.add(periodo)
        session.commit()
        periodo_id = periodo.id

    with Session(engine) as session:
        periodo = session.get(Periodo, periodo_id)
        assert periodo is not None

        cerrar_periodo(
            session,
            periodo,
            actor="sistemas@asiati.com.co",
            motivo="Cierre que será revertido",
        )
        session.flush()
        session.rollback()

    with Session(engine) as session:
        periodo = session.get(Periodo, periodo_id)
        assert periodo is not None
        assert periodo.cerrado is False

        eventos = list(
            session.scalars(
                select(PeriodoCierreEvento).where(
                    PeriodoCierreEvento.periodo_id == periodo_id
                )
            )
        )
        assert eventos == []
