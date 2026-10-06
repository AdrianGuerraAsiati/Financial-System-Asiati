"""Listas de categorización en 7 dimensiones (decisión 0008).

Cinco dimensiones son listas administrables (DIMENSIONES). La modalidad es fija (WALLET) y el tercero es el único
texto libre. El conciliador solo elige valores activos; el coordinador financiero administra las listas.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar_auditoria
from app.core.dimensiones.model import DimensionValor

DIMENSIONES = ("ingreso_egreso", "unidad_negocio", "categoria", "empresa", "fijo_variable")
NOMBRES = {
    "ingreso_egreso": "ingreso/egreso",
    "unidad_negocio": "unidad de negocio",
    "categoria": "categoría",
    "empresa": "empresa",
    "fijo_variable": "fijo/variable",
}
MODALIDADES = ("WALLET",)
LARGO_MAXIMO = 120


class DimensionError(ValueError):
    """Dato inválido para una lista; el mensaje dice qué hacer."""


class DimensionDuplicadaError(DimensionError):
    """Ya existe un valor equivalente en la misma lista."""


@dataclass(frozen=True)
class ResultadoCarga:
    creados: int
    existentes: int


def normalizar(valor: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", valor).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.upper().split())


def _limpio(valor: str | None) -> str:
    texto = " ".join((valor or "").split())
    if not texto:
        raise DimensionError("Escribe el valor: no puede quedar vacío.")
    if len(texto) > LARGO_MAXIMO:
        raise DimensionError(f"El valor es muy largo: usa máximo {LARGO_MAXIMO} caracteres.")
    return texto


def _exigir_dimension(dimension: str) -> None:
    if dimension not in DIMENSIONES:
        raise DimensionError(
            f"La lista {dimension!r} no existe. Usa una de: {', '.join(DIMENSIONES)}."
        )


def _equivalente(session: Session, dimension: str, normalizado: str) -> DimensionValor | None:
    return session.scalar(
        select(DimensionValor).where(
            DimensionValor.dimension == dimension,
            DimensionValor.valor_normalizado == normalizado,
        )
    )


def _json(valor: DimensionValor) -> dict[str, Any]:
    return {"dimension": valor.dimension, "valor": valor.valor, "activo": valor.activo}


def listar_valores(
    session: Session, *, dimension: str | None = None, incluir_inactivos: bool = False
) -> list[DimensionValor]:
    consulta = select(DimensionValor).order_by(DimensionValor.dimension, DimensionValor.valor_normalizado)
    if dimension is not None:
        _exigir_dimension(dimension)
        consulta = consulta.where(DimensionValor.dimension == dimension)
    if not incluir_inactivos:
        consulta = consulta.where(DimensionValor.activo.is_(True))
    return list(session.scalars(consulta))


def crear_valor(
    session: Session, *, dimension: str, valor: str, usuario_id: int, ip: str | None
) -> DimensionValor:
    _exigir_dimension(dimension)
    texto = _limpio(valor)
    existente = _equivalente(session, dimension, normalizar(texto))
    if existente is not None:
        estado = "activo" if existente.activo else "desactivado; actívalo en vez de crearlo"
        raise DimensionDuplicadaError(
            f'Ya existe "{existente.valor}" en {NOMBRES[dimension]} ({estado}).'
        )
    nuevo = DimensionValor(dimension=dimension, valor=texto, valor_normalizado=normalizar(texto), activo=True)
    session.add(nuevo)
    session.flush()
    registrar_auditoria(
        session,
        usuario_id=usuario_id,
        accion="dimension.crear",
        entidad="dimension_valor",
        entidad_id=nuevo.id,
        despues=_json(nuevo),
        ip=ip,
    )
    return nuevo


def actualizar_valor(
    session: Session,
    valor: DimensionValor,
    *,
    nuevo_valor: str | None,
    activo: bool | None,
    usuario_id: int,
    ip: str | None,
) -> DimensionValor:
    antes = _json(valor)
    if nuevo_valor is not None:
        texto = _limpio(nuevo_valor)
        otro = _equivalente(session, valor.dimension, normalizar(texto))
        if otro is not None and otro.id != valor.id:
            raise DimensionDuplicadaError(
                f'Ya existe "{otro.valor}" en {NOMBRES[valor.dimension]}. Usa ese o elige otro nombre.'
            )
        valor.valor = texto
        valor.valor_normalizado = normalizar(texto)
    if activo is not None:
        valor.activo = activo
    session.flush()
    registrar_auditoria(
        session,
        usuario_id=usuario_id,
        accion="dimension.actualizar",
        entidad="dimension_valor",
        entidad_id=valor.id,
        antes=antes,
        despues=_json(valor),
        ip=ip,
    )
    return valor


def cargar_valores_iniciales(session: Session, valores: dict[str, list[str]]) -> ResultadoCarga:
    """Crea lo que falte. No renombra, no reactiva ni desactiva lo existente."""
    creados = existentes = 0
    for dimension, lista in valores.items():
        _exigir_dimension(dimension)
        for valor in lista:
            texto = _limpio(valor)
            if _equivalente(session, dimension, normalizar(texto)) is not None:
                existentes += 1
                continue
            session.add(
                DimensionValor(dimension=dimension, valor=texto, valor_normalizado=normalizar(texto), activo=True)
            )
            session.flush()
            creados += 1
    return ResultadoCarga(creados=creados, existentes=existentes)


def validar_categorizacion(
    session: Session,
    datos: dict[str, Any],
    *,
    usuario_id: int,
    empresa_esperada: str | None = None,
) -> dict[str, Any]:
    """Valida las 7 dimensiones contra las listas activas y devuelve el dato a guardar."""
    resultado: dict[str, Any] = {}
    ids: dict[str, int] = {}
    for dimension in DIMENSIONES:
        crudo = datos.get(dimension)
        if crudo is None or not str(crudo).strip():
            raise DimensionError(f"Elige un valor de {NOMBRES[dimension]}: es obligatorio.")
        valor = _equivalente(session, dimension, normalizar(str(crudo)))
        if valor is None or not valor.activo:
            raise DimensionError(
                f'El valor "{crudo}" no está en la lista de {NOMBRES[dimension]}. '
                "Elige uno de la lista; si ninguno sirve, escala al coordinador."
            )
        resultado[dimension] = valor.valor
        ids[dimension] = valor.id

    if empresa_esperada is not None and normalizar(resultado["empresa"]) != normalizar(empresa_esperada):
        raise DimensionError(
            f'La empresa debe ser "{empresa_esperada}" porque sale de la wallet y no se edita.'
        )

    modalidad = str(datos.get("modalidad") or "").strip().upper()
    if modalidad not in MODALIDADES:
        raise DimensionError(f"La modalidad debe ser {' o '.join(MODALIDADES)}.")
    tercero = " ".join(str(datos.get("tercero") or "").split())
    if len(tercero) > 200:
        raise DimensionError("El tercero es muy largo: usa máximo 200 caracteres.")

    return {
        **resultado,
        "modalidad": modalidad,
        "tercero": tercero or None,
        "valor_ids": ids,
        "usuario_id": usuario_id,
        "fecha": datetime.now(timezone.utc).isoformat(),
    }
