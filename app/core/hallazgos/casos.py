"""Consultas y acciones del caso especial sobre hallazgos del núcleo."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar_auditoria
from app.core.hallazgos.escalamiento import (
    transicion_escalar,
    transicion_observar,
    transicion_responder,
)
from app.core.hallazgos.mensajes import (
    TIPO_NOTA,
    TIPO_PREGUNTA,
    TIPO_RESPUESTA,
    HallazgoMensaje,
)
from app.core.hallazgos.model import Hallazgo
from app.core.periodos import Periodo
from app.core.periodos.errors import PeriodoCerradoError


def empresa_del_hallazgo(session: Session, hallazgo_id: int) -> int | None:
    return session.scalar(
        select(Periodo.empresa_id)
        .join(Hallazgo, Hallazgo.periodo_id == Periodo.id)
        .where(Hallazgo.id == hallazgo_id)
    )


def listar_hallazgos(
    session: Session,
    *,
    empresas_visibles: frozenset[int] | None,
    estado: str | None = None,
    periodo_id: int | None = None,
) -> list[tuple[Hallazgo, int]]:
    """Hallazgos con su empresa. El filtro de empresas va aquí, no en el endpoint."""
    consulta = (
        select(Hallazgo, Periodo.empresa_id)
        .join(Periodo, Periodo.id == Hallazgo.periodo_id)
        .order_by(Hallazgo.id)
    )
    if empresas_visibles is not None:
        consulta = consulta.where(Periodo.empresa_id.in_(empresas_visibles))
    if estado is not None:
        consulta = consulta.where(Hallazgo.estado == estado)
    if periodo_id is not None:
        consulta = consulta.where(Hallazgo.periodo_id == periodo_id)
    return [(hallazgo, empresa_id) for hallazgo, empresa_id in session.execute(consulta)]


def mensajes_del_hallazgo(session: Session, hallazgo_id: int) -> list[HallazgoMensaje]:
    return list(
        session.scalars(
            select(HallazgoMensaje)
            .where(HallazgoMensaje.hallazgo_id == hallazgo_id)
            .order_by(HallazgoMensaje.id)
        )
    )


def _exigir_periodo_abierto(session: Session, hallazgo: Hallazgo) -> Periodo:
    periodo = session.get(Periodo, hallazgo.periodo_id)
    if periodo.cerrado:
        raise PeriodoCerradoError(
            "El período de este hallazgo está cerrado y no se modifica. "
            "Si hay que cambiar algo, pide al superadministrador que lo reabra."
        )
    return periodo


def escalar_hallazgo(
    session: Session,
    hallazgo: Hallazgo,
    *,
    usuario_id: int,
    pregunta: str | None,
    ip: str | None,
) -> Hallazgo:
    nuevo_estado = transicion_escalar(hallazgo.estado, pregunta)
    periodo = _exigir_periodo_abierto(session, hallazgo)
    texto = pregunta.strip()
    antes = {"estado": hallazgo.estado}

    hallazgo.estado = nuevo_estado
    session.add(
        HallazgoMensaje(
            hallazgo_id=hallazgo.id,
            usuario_id=usuario_id,
            tipo=TIPO_PREGUNTA,
            texto=texto,
        )
    )
    registrar_auditoria(
        session,
        usuario_id=usuario_id,
        empresa_id=periodo.empresa_id,
        accion="hallazgo.escalar",
        entidad="hallazgo",
        entidad_id=hallazgo.id,
        antes=antes,
        despues={"estado": nuevo_estado, "pregunta": texto},
        ip=ip,
    )
    return hallazgo


def responder_escalado(
    session: Session,
    hallazgo: Hallazgo,
    *,
    usuario_id: int,
    respuesta: str | None,
    resolver: bool,
    ip: str | None,
) -> Hallazgo:
    nuevo_estado = transicion_responder(hallazgo.estado, respuesta, resolver=resolver)
    periodo = _exigir_periodo_abierto(session, hallazgo)
    texto = respuesta.strip()
    antes = {"estado": hallazgo.estado, "resuelto": hallazgo.resuelto}

    hallazgo.estado = nuevo_estado
    if resolver:
        hallazgo.resuelto = True
    session.add(
        HallazgoMensaje(
            hallazgo_id=hallazgo.id,
            usuario_id=usuario_id,
            tipo=TIPO_RESPUESTA,
            texto=texto,
        )
    )
    registrar_auditoria(
        session,
        usuario_id=usuario_id,
        empresa_id=periodo.empresa_id,
        accion="hallazgo.responder_escalado",
        entidad="hallazgo",
        entidad_id=hallazgo.id,
        antes=antes,
        despues={
            "estado": nuevo_estado,
            "resuelto": hallazgo.resuelto,
            "respuesta": texto,
        },
        ip=ip,
    )
    return hallazgo


def observar_hallazgo(
    session: Session,
    hallazgo: Hallazgo,
    *,
    usuario_id: int,
    observacion: str | None,
    resolver: bool,
    ip: str | None,
) -> Hallazgo:
    nuevo_estado = transicion_observar(hallazgo.estado, observacion, resolver=resolver)
    periodo = _exigir_periodo_abierto(session, hallazgo)
    texto = observacion.strip()
    antes = {"estado": hallazgo.estado, "resuelto": hallazgo.resuelto}

    hallazgo.estado = nuevo_estado
    if resolver:
        hallazgo.resuelto = True
    session.add(
        HallazgoMensaje(
            hallazgo_id=hallazgo.id,
            usuario_id=usuario_id,
            tipo=TIPO_NOTA,
            texto=texto,
        )
    )
    registrar_auditoria(
        session,
        usuario_id=usuario_id,
        empresa_id=periodo.empresa_id,
        accion="hallazgo.observar",
        entidad="hallazgo",
        entidad_id=hallazgo.id,
        antes=antes,
        despues={
            "estado": nuevo_estado,
            "resuelto": hallazgo.resuelto,
            "observacion": texto,
        },
        ip=ip,
    )
    return hallazgo
