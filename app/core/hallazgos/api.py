from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth.dependencias import Acceso, requiere
from app.core.dimensiones.service import DimensionError, validar_categorizacion
from app.core.empresas import Empresa
from app.core.permisos import RecursoNoVisibleError, SinPermisoError, verificar_acceso
from app.core.hallazgos.casos import (
    empresa_del_hallazgo,
    escalar_hallazgo,
    listar_hallazgos,
    mensajes_del_hallazgo,
    observar_hallazgo,
    responder_escalado,
)
from app.core.hallazgos.escalamiento import (
    ESTADOS,
    EscalamientoInvalidoError,
    TextoObligatorioError,
)
from app.core.hallazgos.model import Hallazgo
from app.core.periodos.errors import PeriodoCerradoError
from app.core.session import obtener_session


router = APIRouter(prefix="/hallazgos", tags=["hallazgos"])


def empresa_de_hallazgo(
    hallazgo_id: int,
    session: Session = Depends(obtener_session),
) -> int | None:
    return empresa_del_hallazgo(session, hallazgo_id)


class EscalarEntrada(BaseModel):
    pregunta: str | None = None


class ObservarEntrada(BaseModel):
    observacion: str | None = None
    resolver: bool = False
    # Las 7 dimensiones (decisión 0008). Opcional: sin ella, observar funciona como antes.
    categorizacion: dict[str, str | None] | None = None


class ResponderEntrada(BaseModel):
    respuesta: str | None = None
    resolver: bool = False


def _hallazgo_json(hallazgo: Hallazgo, empresa_id: int) -> dict[str, object]:
    return {
        "id": hallazgo.id,
        "empresa_id": empresa_id,
        "periodo_id": hallazgo.periodo_id,
        "motor_slug": hallazgo.motor_slug,
        "codigo_regla": hallazgo.codigo_regla,
        "descripcion": hallazgo.descripcion,
        "critico": hallazgo.critico,
        "resuelto": hallazgo.resuelto,
        "estado": hallazgo.estado,
        "resuelto_por_sistema": hallazgo.resuelto_por_sistema,
        "clave": hallazgo.clave,
        "evidencia": hallazgo.evidencia,
    }


@router.get("")
def consultar_hallazgos(
    estado: str | None = None,
    periodo_id: int | None = None,
    acceso: Acceso = Depends(requiere("conciliacion.ver")),
    session: Session = Depends(obtener_session),
) -> list[dict[str, object]]:
    if estado is not None and estado not in ESTADOS:
        raise HTTPException(
            status_code=422,
            detail=f"Estado no válido: {estado}. Usa uno de: {', '.join(ESTADOS)}.",
        )
    return [
        _hallazgo_json(hallazgo, empresa_id)
        for hallazgo, empresa_id in listar_hallazgos(
            session,
            empresas_visibles=acceso.empresas_visibles,
            estado=estado,
            periodo_id=periodo_id,
        )
    ]


@router.get("/{hallazgo_id}")
def detalle_hallazgo(
    hallazgo_id: int,
    acceso: Acceso = Depends(
        requiere("conciliacion.ver", empresa_de=empresa_de_hallazgo)
    ),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    # requiere(...) ya comprobó que existe y que la empresa es visible.
    hallazgo = session.get(Hallazgo, hallazgo_id)
    return {
        **_hallazgo_json(hallazgo, empresa_del_hallazgo(session, hallazgo_id)),
        "mensajes": [
            {
                "id": mensaje.id,
                "tipo": mensaje.tipo,
                "usuario_id": mensaje.usuario_id,
                "texto": mensaje.texto,
                "creado_at": mensaje.creado_at.isoformat(),
            }
            for mensaje in mensajes_del_hallazgo(session, hallazgo_id)
        ],
    }


def _ejecutar_caso(session: Session, accion) -> Hallazgo:
    try:
        hallazgo = accion()
        session.commit()
    except TextoObligatorioError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (EscalamientoInvalidoError, PeriodoCerradoError) as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return hallazgo


@router.post("/{hallazgo_id}/escalar")
def escalar(
    hallazgo_id: int,
    datos: EscalarEntrada,
    acceso: Acceso = Depends(
        requiere("hallazgos.escalar", empresa_de=empresa_de_hallazgo)
    ),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    hallazgo = session.get(Hallazgo, hallazgo_id)
    _ejecutar_caso(
        session,
        lambda: escalar_hallazgo(
            session,
            hallazgo,
            usuario_id=acceso.usuario.id,
            pregunta=datos.pregunta,
            ip=acceso.ip,
        ),
    )
    return _hallazgo_json(hallazgo, empresa_del_hallazgo(session, hallazgo_id))


@router.post("/{hallazgo_id}/observar")
def observar(
    hallazgo_id: int,
    datos: ObservarEntrada,
    acceso: Acceso = Depends(
        requiere("hallazgos.gestionar", empresa_de=empresa_de_hallazgo)
    ),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    hallazgo = session.get(Hallazgo, hallazgo_id)
    categorizacion = None
    if datos.categorizacion is not None:
        empresa_id = empresa_del_hallazgo(session, hallazgo_id)
        try:
            verificar_acceso(
                acceso.usuario.rol,
                "movimientos.categorizar",
                empresa_id=empresa_id,
                asignadas=acceso.empresas_visibles or frozenset(),
            )
        except (SinPermisoError, RecursoNoVisibleError) as exc:
            raise HTTPException(status_code=403, detail="Tu rol no puede categorizar movimientos.") from exc
        empresa = session.get(Empresa, empresa_id)
        try:
            categorizacion = validar_categorizacion(
                session,
                datos.categorizacion,
                usuario_id=acceso.usuario.id,
                empresa_esperada=empresa.nombre,
            )
        except DimensionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    _ejecutar_caso(
        session,
        lambda: observar_hallazgo(
            session,
            hallazgo,
            usuario_id=acceso.usuario.id,
            observacion=datos.observacion,
            resolver=datos.resolver,
            ip=acceso.ip,
            categorizacion=categorizacion,
        ),
    )
    return _hallazgo_json(hallazgo, empresa_del_hallazgo(session, hallazgo_id))


@router.post("/{hallazgo_id}/responder")
def responder(
    hallazgo_id: int,
    datos: ResponderEntrada,
    acceso: Acceso = Depends(
        requiere("hallazgos.responder_escalado", empresa_de=empresa_de_hallazgo)
    ),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    hallazgo = session.get(Hallazgo, hallazgo_id)
    _ejecutar_caso(
        session,
        lambda: responder_escalado(
            session,
            hallazgo,
            usuario_id=acceso.usuario.id,
            respuesta=datos.respuesta,
            resolver=datos.resolver,
            ip=acceso.ip,
        ),
    )
    return _hallazgo_json(hallazgo, empresa_del_hallazgo(session, hallazgo_id))
