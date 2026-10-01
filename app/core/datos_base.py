from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.empresas import Empresa
from app.core.fuentes import Fuente
from app.core.periodos import Periodo
from app.core.session import crear_session


class PeriodoDatosBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha_inicio: date
    fecha_fin: date
    cerrado: bool = False

    @model_validator(mode="after")
    def validar_rango(self) -> "PeriodoDatosBase":
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser anterior a fecha_inicio.")
        return self


class EmpresaDatosBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str
    periodos: list[PeriodoDatosBase]
    fuentes: list[str]

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, valor: str) -> str:
        limpio = valor.strip()
        if not limpio:
            raise ValueError("El nombre de la empresa es obligatorio.")
        return limpio

    @field_validator("fuentes")
    @classmethod
    def validar_fuentes(cls, valores: list[str]) -> list[str]:
        limpias = [valor.strip() for valor in valores]
        if any(not valor for valor in limpias):
            raise ValueError("Los nombres de fuente no pueden estar vacíos.")
        if len(set(limpias)) != len(limpias):
            raise ValueError("No repitas una fuente dentro de la misma empresa.")
        return limpias


class DatosBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    empresas: list[EmpresaDatosBase]

    @model_validator(mode="after")
    def validar_empresas_unicas(self) -> "DatosBase":
        nombres = [empresa.nombre for empresa in self.empresas]
        if len(set(nombres)) != len(nombres):
            raise ValueError("No repitas una empresa en el archivo de datos base.")
        return self


def leer_datos_base(ruta: str | Path) -> DatosBase:
    path = Path(ruta)
    with path.open("r", encoding="utf-8") as archivo:
        contenido = json.load(archivo)
    return DatosBase.model_validate(contenido)


def _empresa_exacta(session: Session, nombre: str) -> Empresa | None:
    empresas = list(session.scalars(select(Empresa).where(Empresa.nombre == nombre)))
    if len(empresas) > 1:
        raise RuntimeError(
            f'Hay más de una empresa con el nombre exacto "{nombre}". '
            "Corrige el catálogo antes de continuar."
        )
    return empresas[0] if empresas else None


def _fuente_exacta(
    session: Session,
    *,
    empresa_id: int,
    nombre: str,
) -> Fuente | None:
    fuentes = list(
        session.scalars(
            select(Fuente).where(
                Fuente.empresa_id == empresa_id,
                Fuente.nombre == nombre,
            )
        )
    )
    if len(fuentes) > 1:
        raise RuntimeError(
            f'La empresa {empresa_id} tiene más de una fuente "{nombre}". '
            "Corrige el catálogo antes de continuar."
        )
    return fuentes[0] if fuentes else None


def _periodo_exacto(
    session: Session,
    *,
    empresa_id: int,
    fecha_inicio: date,
    fecha_fin: date,
) -> Periodo | None:
    return session.scalar(
        select(Periodo).where(
            Periodo.empresa_id == empresa_id,
            Periodo.fecha_inicio == fecha_inicio,
            Periodo.fecha_fin == fecha_fin,
        )
    )


def aplicar_datos_base(session: Session, datos: DatosBase) -> dict[str, object]:
    resumen: dict[str, int | list[dict[str, object]]] = {
        "empresas_creadas": 0,
        "empresas_reutilizadas": 0,
        "periodos_creados": 0,
        "periodos_reutilizados": 0,
        "fuentes_creadas": 0,
        "fuentes_reutilizadas": 0,
        "empresas": [],
    }

    empresas_resultado: list[dict[str, object]] = []

    for empresa_spec in datos.empresas:
        empresa = _empresa_exacta(session, empresa_spec.nombre)
        if empresa is None:
            empresa = Empresa(nombre=empresa_spec.nombre)
            session.add(empresa)
            session.flush()
            resumen["empresas_creadas"] += 1
        else:
            resumen["empresas_reutilizadas"] += 1

        periodos_resultado: list[dict[str, object]] = []
        for periodo_spec in empresa_spec.periodos:
            periodo = _periodo_exacto(
                session,
                empresa_id=empresa.id,
                fecha_inicio=periodo_spec.fecha_inicio,
                fecha_fin=periodo_spec.fecha_fin,
            )
            if periodo is None:
                periodo = Periodo(
                    empresa_id=empresa.id,
                    fecha_inicio=periodo_spec.fecha_inicio,
                    fecha_fin=periodo_spec.fecha_fin,
                    cerrado=periodo_spec.cerrado,
                )
                session.add(periodo)
                session.flush()
                resumen["periodos_creados"] += 1
            else:
                if periodo.cerrado != periodo_spec.cerrado:
                    estado_actual = "cerrado" if periodo.cerrado else "abierto"
                    estado_pedido = "cerrado" if periodo_spec.cerrado else "abierto"
                    raise RuntimeError(
                        f"El período {periodo.id} de {empresa.nombre} ya existe "
                        f"{estado_actual}, pero el archivo pide dejarlo {estado_pedido}. "
                        "No se cambia el estado automáticamente: usa el flujo auditable "
                        "de cierre o reapertura."
                    )
                resumen["periodos_reutilizados"] += 1

            periodos_resultado.append(
                {
                    "id": periodo.id,
                    "fecha_inicio": periodo.fecha_inicio.isoformat(),
                    "fecha_fin": periodo.fecha_fin.isoformat(),
                    "cerrado": periodo.cerrado,
                }
            )

        fuentes_resultado: list[dict[str, object]] = []
        for nombre_fuente in empresa_spec.fuentes:
            fuente = _fuente_exacta(
                session,
                empresa_id=empresa.id,
                nombre=nombre_fuente,
            )
            if fuente is None:
                fuente = Fuente(empresa_id=empresa.id, nombre=nombre_fuente)
                session.add(fuente)
                session.flush()
                resumen["fuentes_creadas"] += 1
            else:
                resumen["fuentes_reutilizadas"] += 1

            fuentes_resultado.append({"id": fuente.id, "nombre": fuente.nombre})

        empresas_resultado.append(
            {
                "id": empresa.id,
                "nombre": empresa.nombre,
                "periodos": periodos_resultado,
                "fuentes": fuentes_resultado,
            }
        )

    resumen["empresas"] = empresas_resultado
    return resumen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Crea o reutiliza empresas, períodos y fuentes del núcleo desde un JSON. "
            "Es idempotente y no cambia el estado de períodos existentes."
        )
    )
    parser.add_argument(
        "--archivo",
        required=True,
        help="Ruta al JSON de datos base. El archivo real no debe versionarse.",
    )
    argumentos = parser.parse_args(argv)

    datos = leer_datos_base(argumentos.archivo)
    with crear_session() as session:
        try:
            resumen = aplicar_datos_base(session, datos)
            session.commit()
        except Exception:
            session.rollback()
            raise

    print(json.dumps(resumen, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
