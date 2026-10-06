"""Sincronización de hallazgos de motor por clave estable (decisión 0008).

Al volver a conciliar con un archivo nuevo, el motor entrega la lista completa de hallazgos de un alcance
(por ejemplo, una wallet en un período). Por cada clave:

- si ya existe, se actualiza la evidencia y se conserva lo que hizo la gente: estado, mensajes, escalamiento y
  categorización (`CLAVES_EVIDENCIA_DE_PERSONAS`);
- si fue resuelto por el sistema y reaparece, se reabre como detectado con nota automática;
- si lo resolvió una persona y sigue apareciendo, se queda resuelto: solo cambia la evidencia;
- si no existe, se crea.

Lo que estaba abierto en el alcance y ya no aparece queda "resuelto por el sistema" con nota automática.
Las notas automáticas las firma quien ejecutó la conciliación. Nada se borra.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar_auditoria
from app.core.hallazgos.escalamiento import ESTADO_CERRADO, ESTADO_DETECTADO, ESTADO_RESUELTO
from app.core.hallazgos.mensajes import TIPO_SISTEMA, HallazgoMensaje
from app.core.hallazgos.model import Hallazgo
from app.core.periodos import Periodo
from app.core.periodos.errors import PeriodoCerradoError

# Claves de la evidencia que escriben personas, no el motor: se conservan al actualizar.
CLAVES_EVIDENCIA_DE_PERSONAS = ("categorizacion",)
ESTADOS_CERRADOS = (ESTADO_RESUELTO, ESTADO_CERRADO)

NOTA_RESUELTO_POR_SISTEMA = (
    "Resuelto por el sistema: el problema ya no aparece en la carga más reciente."
)
NOTA_REABIERTO = (
    "Reabierto por el sistema: el problema reapareció en una carga posterior. Revísalo de nuevo."
)


@dataclass(frozen=True)
class HallazgoMotorNuevo:
    clave: str
    codigo_regla: str
    descripcion: str
    evidencia: dict[str, Any]
    critico: bool


@dataclass(frozen=True)
class ResultadoSincronizacion:
    creados: int
    actualizados: int
    reabiertos: int
    resueltos_por_sistema: int


def _nota(session: Session, hallazgo: Hallazgo, usuario_id: int, texto: str) -> None:
    session.add(
        HallazgoMensaje(hallazgo_id=hallazgo.id, usuario_id=usuario_id, tipo=TIPO_SISTEMA, texto=texto)
    )


def _auditar(session: Session, hallazgo: Hallazgo, *, usuario_id: int, empresa_id: int, accion: str, antes: dict) -> None:
    registrar_auditoria(
        session,
        usuario_id=usuario_id,
        empresa_id=empresa_id,
        accion=accion,
        entidad="hallazgo",
        entidad_id=hallazgo.id,
        antes=antes,
        despues={"estado": hallazgo.estado, "resuelto": hallazgo.resuelto},
    )


def sincronizar_hallazgos_motor(
    session: Session,
    *,
    periodo_id: int,
    motor_slug: str,
    alcance_clave: str,
    hallazgos: list[HallazgoMotorNuevo],
    usuario_id: int,
) -> ResultadoSincronizacion:
    """`alcance_clave` es el prefijo común de las claves que entrega esta carga (p. ej. una wallet)."""
    periodo = session.get(Periodo, periodo_id)
    if periodo is None:
        raise ValueError("El período no existe.")
    if periodo.cerrado:
        raise PeriodoCerradoError(
            "El período está cerrado y sus hallazgos no se modifican. Reábrelo antes de conciliar."
        )
    fuera = [h.clave for h in hallazgos if not h.clave.startswith(alcance_clave)]
    if fuera:
        raise ValueError(f"La clave {fuera[0]} no pertenece al alcance {alcance_clave}.")

    existentes = {
        h.clave: h
        for h in session.scalars(
            select(Hallazgo).where(
                Hallazgo.periodo_id == periodo_id,
                Hallazgo.motor_slug == motor_slug,
                Hallazgo.clave.startswith(alcance_clave, autoescape=True),
            )
        )
    }
    creados = actualizados = reabiertos = resueltos = 0
    vistas: set[str] = set()

    for nuevo in hallazgos:
        vistas.add(nuevo.clave)
        actual = existentes.get(nuevo.clave)
        if actual is None:
            session.add(
                Hallazgo(
                    periodo_id=periodo_id,
                    motor_slug=motor_slug,
                    clave=nuevo.clave,
                    codigo_regla=nuevo.codigo_regla,
                    descripcion=nuevo.descripcion,
                    evidencia=nuevo.evidencia,
                    critico=nuevo.critico,
                    resuelto=False,
                )
            )
            creados += 1
            continue

        conservadas = {k: v for k, v in (actual.evidencia or {}).items() if k in CLAVES_EVIDENCIA_DE_PERSONAS}
        actual.evidencia = {**nuevo.evidencia, **conservadas}
        actual.descripcion = nuevo.descripcion
        actual.critico = nuevo.critico
        actualizados += 1
        if actual.estado == ESTADO_RESUELTO and actual.resuelto_por_sistema:
            antes = {"estado": actual.estado, "resuelto": actual.resuelto}
            actual.estado = ESTADO_DETECTADO
            actual.resuelto = False
            actual.resuelto_por_sistema = False
            _nota(session, actual, usuario_id, NOTA_REABIERTO)
            _auditar(session, actual, usuario_id=usuario_id, empresa_id=periodo.empresa_id,
                     accion="hallazgo.reabrir_sistema", antes=antes)
            reabiertos += 1

    for clave, actual in existentes.items():
        if clave in vistas or actual.estado in ESTADOS_CERRADOS:
            continue
        antes = {"estado": actual.estado, "resuelto": actual.resuelto}
        actual.estado = ESTADO_RESUELTO
        actual.resuelto = True
        actual.resuelto_por_sistema = True
        _nota(session, actual, usuario_id, NOTA_RESUELTO_POR_SISTEMA)
        _auditar(session, actual, usuario_id=usuario_id, empresa_id=periodo.empresa_id,
                 accion="hallazgo.resolver_sistema", antes=antes)
        resueltos += 1

    session.flush()
    return ResultadoSincronizacion(
        creados=creados,
        actualizados=actualizados,
        reabiertos=reabiertos,
        resueltos_por_sistema=resueltos,
    )
