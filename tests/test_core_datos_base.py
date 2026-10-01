import uuid
from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.datos_base import DatosBase, aplicar_datos_base
from app.core.empresas import Empresa
from app.core.fuentes import Fuente
from app.core.periodos import Periodo
from tests.apoyo_auth import engine


def _datos(nombre: str, *, cerrado: bool = False) -> DatosBase:
    return DatosBase.model_validate(
        {
            "empresas": [
                {
                    "nombre": nombre,
                    "periodos": [
                        {
                            "fecha_inicio": "2026-09-01",
                            "fecha_fin": "2026-09-30",
                            "cerrado": cerrado,
                        }
                    ],
                    "fuentes": ["Wallet Menpros", "Órdenes Dropi"],
                }
            ]
        }
    )


def test_datos_base_crea_y_luego_reutiliza_sin_duplicar() -> None:
    nombre = f"Empresa datos base {uuid.uuid4().hex[:8]}"
    datos = _datos(nombre)

    with Session(engine()) as session:
        primero = aplicar_datos_base(session, datos)
        session.commit()

    assert primero["empresas_creadas"] == 1
    assert primero["periodos_creados"] == 1
    assert primero["fuentes_creadas"] == 2

    with Session(engine()) as session:
        segundo = aplicar_datos_base(session, datos)
        session.commit()

    assert segundo["empresas_creadas"] == 0
    assert segundo["empresas_reutilizadas"] == 1
    assert segundo["periodos_creados"] == 0
    assert segundo["periodos_reutilizados"] == 1
    assert segundo["fuentes_creadas"] == 0
    assert segundo["fuentes_reutilizadas"] == 2

    with Session(engine()) as session:
        empresa = session.scalar(select(Empresa).where(Empresa.nombre == nombre))
        assert empresa is not None
        assert session.scalar(
            select(func.count())
            .select_from(Periodo)
            .where(Periodo.empresa_id == empresa.id)
        ) == 1
        assert session.scalar(
            select(func.count())
            .select_from(Fuente)
            .where(Fuente.empresa_id == empresa.id)
        ) == 2


def test_datos_base_no_cambia_estado_de_periodo_existente() -> None:
    nombre = f"Empresa estado periodo {uuid.uuid4().hex[:8]}"

    with Session(engine()) as session:
        aplicar_datos_base(session, _datos(nombre, cerrado=False))
        session.commit()

    with Session(engine()) as session:
        with pytest.raises(RuntimeError, match="flujo auditable"):
            aplicar_datos_base(session, _datos(nombre, cerrado=True))
        session.rollback()

    with Session(engine()) as session:
        empresa = session.scalar(select(Empresa).where(Empresa.nombre == nombre))
        assert empresa is not None
        periodo = session.scalar(
            select(Periodo).where(
                Periodo.empresa_id == empresa.id,
                Periodo.fecha_inicio == date(2026, 9, 1),
                Periodo.fecha_fin == date(2026, 9, 30),
            )
        )
        assert periodo is not None
        assert periodo.cerrado is False


def test_datos_base_rechaza_fuentes_repetidas_en_el_archivo() -> None:
    with pytest.raises(ValueError, match="No repitas una fuente"):
        DatosBase.model_validate(
            {
                "empresas": [
                    {
                        "nombre": "Empresa inválida",
                        "periodos": [
                            {
                                "fecha_inicio": "2026-09-01",
                                "fecha_fin": "2026-09-30",
                                "cerrado": False,
                            }
                        ],
                        "fuentes": ["Wallet A", "Wallet A"],
                    }
                ]
            }
        )
