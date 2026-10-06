"""Cargas reutilizables de los archivos de Dropi (decisión 6-oct, Juan Felipe Parra).

Un mismo archivo (mismo hash) se reutiliza si es de la misma empresa, el mismo período y la misma fuente: así se
puede reconciliar una wallet nueva con el mismo reporte de órdenes. En otro período o con otra fuente es un error.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cargas import Carga, calcular_hash_contenido, registrar_carga

MENSAJE_CONCILIACION_REPETIDA = "Estos archivos ya se conciliaron para este período."


class CargaDuplicadaError(ValueError):
    """El archivo ya se cargó en la empresa y no se puede reutilizar aquí."""


class ConciliacionRepetidaError(ValueError):
    """Todos los archivos son idénticos a una conciliación anterior del mismo período."""


def carga_reutilizable(
    session: Session, *, empresa_id: int, periodo_id: int, fuente_id: int, contenido: bytes, que: str
) -> tuple[Carga, bool]:
    """Devuelve (carga, reutilizada). `que` nombra el archivo en el mensaje de error."""
    hash_ = calcular_hash_contenido(contenido)
    existente = session.scalar(
        select(Carga).where(Carga.empresa_id == empresa_id, Carga.contenido_hash == hash_)
    )
    if existente is None:
        carga = registrar_carga(
            session, empresa_id=empresa_id, fuente_id=fuente_id, periodo_id=periodo_id, contenido_hash=hash_
        )
        session.flush()
        return carga, False
    if existente.periodo_id == periodo_id and existente.fuente_id == fuente_id:
        return existente, True
    raise CargaDuplicadaError(
        f"Este {que} ya se cargó en la empresa para otro período o con otra fuente. "
        "Usa el archivo del período que estás conciliando."
    )
