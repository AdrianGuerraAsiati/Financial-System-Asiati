from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.auditoria.service import registrar_auditoria
from app.core.fuentes import Fuente
from app.core.periodos import Periodo
from app.core.periodos.errors import PeriodoCerradoError

from .categorizador import DIMENSIONES_CATEGORIZACION, ResultadoCategorizacion, categorizar
from .model import Movimiento, ReglaCategorizacion


CAMPOS_CATEGORIA = (*DIMENSIONES_CATEGORIZACION, "ciudad")


def empresa_del_movimiento(session: Session, movimiento_id: int) -> int | None:
    return session.scalar(
        select(Fuente.empresa_id)
        .join(Movimiento, Movimiento.fuente_id == Fuente.id)
        .where(Movimiento.id == movimiento_id)
    )


def empresa_de_fuente(session: Session, fuente_id: int) -> int | None:
    return session.scalar(select(Fuente.empresa_id).where(Fuente.id == fuente_id))


def _asegurar_periodo_abierto(session: Session, periodo_id: int) -> Periodo:
    periodo = session.get(Periodo, periodo_id)
    if periodo is None:
        raise ValueError("No encontramos el período indicado.")
    if periodo.cerrado:
        raise PeriodoCerradoError(
            "El período está cerrado y sus movimientos no pueden recategorizarse."
        )
    return periodo


def _tipo_fuente(movimiento: Movimiento) -> str | None:
    crudo = movimiento.crudo or {}
    for clave in ("tipo_fuente", "tipo_origen", "TIPO", "tipo"):
        valor = crudo.get(clave)
        if valor not in (None, ""):
            return str(valor)
    return None


def _contexto(movimiento: Movimiento) -> dict[str, Any]:
    crudo = movimiento.crudo or {}
    contexto: dict[str, Any] = dict(crudo)
    equivalencias = {
        "empresa": ("empresa", "EMPRESA"),
        "tercero": ("tercero", "TERCERO", "contraparte", "CONTRAPARTE"),
        "unidad_negocio": ("unidad_negocio", "UNIDAD_NEGOCIO", "UNID. NEGOCIO"),
        "modalidad": ("modalidad", "MODALIDAD"),
        "fijo_variable": ("fijo_variable", "FIJO_VARIABLE", "FIJO / VARIABLE"),
        "ciudad": ("ciudad", "CIUDAD"),
    }
    for canonico, claves in equivalencias.items():
        if movimiento.__dict__.get(canonico) not in (None, ""):
            contexto[canonico] = movimiento.__dict__[canonico]
            continue
        for clave in claves:
            if crudo.get(clave) not in (None, ""):
                contexto[canonico] = crudo[clave]
                break
    return contexto


def _aplicar_resultado(
    movimiento: Movimiento,
    resultado: ResultadoCategorizacion,
) -> None:
    movimiento.descripcion_norm = movimiento.descripcion_norm or ""
    movimiento.estado_categoria = resultado.estado
    movimiento.regla_id = resultado.regla_id
    for campo in CAMPOS_CATEGORIA:
        setattr(movimiento, campo, getattr(resultado, campo))


def listar_movimientos(
    session: Session,
    *,
    empresas_visibles: frozenset[int] | None,
    periodo_id: int | None = None,
    fuente_id: int | None = None,
    estado_categoria: str | None = None,
    categoria: str | None = None,
    q: str | None = None,
    offset: int = 0,
    limite: int = 200,
) -> tuple[Movimiento, ...]:
    statement = (
        select(Movimiento)
        .join(Fuente, Fuente.id == Movimiento.fuente_id)
        .order_by(Movimiento.fecha.desc(), Movimiento.id.desc())
    )
    if empresas_visibles is not None:
        statement = statement.where(Fuente.empresa_id.in_(empresas_visibles))
    if periodo_id is not None:
        statement = statement.where(Movimiento.periodo_id == periodo_id)
    if fuente_id is not None:
        statement = statement.where(Movimiento.fuente_id == fuente_id)
    if estado_categoria is not None:
        statement = statement.where(Movimiento.estado_categoria == estado_categoria)
    if categoria is not None:
        statement = statement.where(Movimiento.categoria == categoria)
    if q:
        termino = f"%{q.strip()}%"
        statement = statement.where(
            or_(
                Movimiento.descripcion.ilike(termino),
                Movimiento.referencia_externa.ilike(termino),
            )
        )
    return tuple(session.scalars(statement.offset(offset).limit(limite)))


def categorizar_manual(
    session: Session,
    movimiento: Movimiento,
    *,
    cambios: Mapping[str, str | None],
    usuario_id: int,
    ip: str | None,
) -> dict[str, object]:
    _asegurar_periodo_abierto(session, movimiento.periodo_id)
    antes = movimiento_como_dict(movimiento)

    for campo, valor in cambios.items():
        if campo not in CAMPOS_CATEGORIA:
            raise ValueError(f"Campo de categorización no soportado: {campo}.")
        setattr(movimiento, campo, valor)

    movimiento.estado_categoria = "MANUAL"
    movimiento.regla_id = None
    movimiento.categorizado_por = usuario_id
    movimiento.categorizado_at = datetime.now(timezone.utc)

    despues = movimiento_como_dict(movimiento)
    registrar_auditoria(
        session,
        usuario_id=usuario_id,
        empresa_id=empresa_del_movimiento(session, movimiento.id),
        accion="movimiento.categorizar_manual",
        entidad="movimiento",
        entidad_id=movimiento.id,
        antes=antes,
        despues=despues,
        ip=ip,
    )
    return sugerir_regla(movimiento)


def sugerir_regla(movimiento: Movimiento) -> dict[str, object]:
    return {
        "motor_slug": None,
        "fuente_id": movimiento.fuente_id,
        "patron": movimiento.descripcion_norm,
        "tipo_match": "EXACTO",
        "prioridad": 100,
        "condiciones": {},
        **{campo: getattr(movimiento, campo) for campo in CAMPOS_CATEGORIA},
        "requiere_revision": False,
        "origen": "APRENDIDA",
    }


def recategorizar_periodo(
    session: Session,
    *,
    periodo_id: int,
    motor_slug: str,
    fuente_id: int | None = None,
) -> dict[str, int]:
    _asegurar_periodo_abierto(session, periodo_id)

    reglas = tuple(
        session.scalars(
            select(ReglaCategorizacion)
            .where(
                ReglaCategorizacion.motor_slug == motor_slug,
                ReglaCategorizacion.activa.is_(True),
            )
            .order_by(ReglaCategorizacion.prioridad, ReglaCategorizacion.id)
        )
    )
    statement = select(Movimiento).where(Movimiento.periodo_id == periodo_id)
    if fuente_id is not None:
        statement = statement.where(Movimiento.fuente_id == fuente_id)
    movimientos = tuple(session.scalars(statement.order_by(Movimiento.id)))

    resumen = {"evaluados": 0, "actualizados": 0, "auto": 0, "revisar": 0, "pendiente": 0, "manual_omitidos": 0}
    aplicadas: dict[int, int] = {}

    for movimiento in movimientos:
        if movimiento.estado_categoria == "MANUAL":
            resumen["manual_omitidos"] += 1
            continue
        resumen["evaluados"] += 1
        candidatas = [
            regla
            for regla in reglas
            if regla.fuente_id is None or regla.fuente_id == movimiento.fuente_id
        ]
        resultado = categorizar(
            movimiento.descripcion,
            candidatas,
            tipo_fuente=_tipo_fuente(movimiento),
            monto=movimiento.monto,
            contexto=_contexto(movimiento),
        )
        _aplicar_resultado(movimiento, resultado)
        resumen["actualizados"] += 1
        resumen[resultado.estado.lower()] += 1
        if resultado.regla_id is not None:
            aplicadas[resultado.regla_id] = aplicadas.get(resultado.regla_id, 0) + 1

    for regla in reglas:
        incremento = aplicadas.get(regla.id, 0)
        if incremento:
            regla.veces_aplicada += incremento

    return resumen


def reaplicar_regla(
    session: Session,
    regla: ReglaCategorizacion,
    *,
    periodo_id: int,
    fuente_id: int | None = None,
) -> dict[str, int]:
    _asegurar_periodo_abierto(session, periodo_id)
    fuente_objetivo = regla.fuente_id if regla.fuente_id is not None else fuente_id

    statement = select(Movimiento).where(Movimiento.periodo_id == periodo_id)
    if fuente_objetivo is not None:
        statement = statement.where(Movimiento.fuente_id == fuente_objetivo)

    resumen = {"evaluados": 0, "actualizados": 0, "manual_omitidos": 0}
    for movimiento in session.scalars(statement.order_by(Movimiento.id)):
        if movimiento.estado_categoria == "MANUAL":
            resumen["manual_omitidos"] += 1
            continue
        resumen["evaluados"] += 1
        resultado = categorizar(
            movimiento.descripcion,
            [regla],
            tipo_fuente=_tipo_fuente(movimiento),
            monto=movimiento.monto,
            contexto=_contexto(movimiento),
        )
        if resultado.estado == "PENDIENTE":
            continue
        _aplicar_resultado(movimiento, resultado)
        regla.veces_aplicada += 1
        resumen["actualizados"] += 1
    return resumen


def movimiento_como_dict(movimiento: Movimiento) -> dict[str, object]:
    return {
        "id": movimiento.id,
        "fuente_id": movimiento.fuente_id,
        "carga_id": movimiento.carga_id,
        "periodo_id": movimiento.periodo_id,
        "fecha_pago_oportuno": (
            movimiento.fecha_pago_oportuno.isoformat()
            if movimiento.fecha_pago_oportuno is not None
            else None
        ),
        "fecha": movimiento.fecha.isoformat(),
        "tipo": movimiento.tipo,
        "monto": str(movimiento.monto),
        "descripcion": movimiento.descripcion,
        "descripcion_norm": movimiento.descripcion_norm,
        "ciudad": movimiento.ciudad,
        "unidad_negocio": movimiento.unidad_negocio,
        "categoria": movimiento.categoria,
        "empresa": movimiento.empresa,
        "tercero": movimiento.tercero,
        "modalidad": movimiento.modalidad,
        "fijo_variable": movimiento.fijo_variable,
        "recibo_pago_caja": movimiento.recibo_pago_caja,
        "causacion": movimiento.causacion,
        "estado_categoria": movimiento.estado_categoria,
        "regla_id": movimiento.regla_id,
        "categorizado_por": movimiento.categorizado_por,
        "categorizado_at": (
            movimiento.categorizado_at.isoformat()
            if movimiento.categorizado_at is not None
            else None
        ),
        "referencia_externa": movimiento.referencia_externa,
        "hash_fila": movimiento.hash_fila,
        "crudo": movimiento.crudo,
    }


def regla_como_dict(regla: ReglaCategorizacion) -> dict[str, object]:
    return {
        "id": regla.id,
        "motor_slug": regla.motor_slug,
        "fuente_id": regla.fuente_id,
        "patron": regla.patron,
        "tipo_match": regla.tipo_match,
        "prioridad": regla.prioridad,
        "condiciones": regla.condiciones or {},
        **{campo: getattr(regla, campo) for campo in CAMPOS_CATEGORIA},
        "requiere_revision": regla.requiere_revision,
        "activa": regla.activa,
        "origen": regla.origen,
        "veces_aplicada": regla.veces_aplicada,
        "creado_por": regla.creado_por,
        "creado_at": regla.creado_at.isoformat() if regla.creado_at else None,
    }
