from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.auditoria.service import registrar_auditoria
from app.core.auth.dependencias import Acceso, requiere
from app.core.fuentes import Fuente
from app.core.periodos import Periodo
from app.core.periodos.errors import PeriodoCerradoError
from app.core.permisos import Alcance
from app.core.session import obtener_session

from .categorizador import normalizar_descripcion
from .importador_wallets import reglas_desde_catalogo_wallets
from .model import Movimiento, ReglaCategorizacion
from .service import (
    CAMPOS_CATEGORIA,
    categorizar_manual,
    empresa_de_fuente,
    empresa_del_movimiento,
    listar_movimientos,
    movimiento_como_dict,
    reaplicar_regla,
    recategorizar_periodo,
    regla_como_dict,
)


router = APIRouter(tags=["movimientos"])


ESTADOS_CATEGORIA = {"AUTO", "REVISAR", "PENDIENTE", "MANUAL"}
TIPOS_MATCH = {"EXACTO", "EMPIEZA_CON", "CONTIENE", "REGEX"}


def _empresa_de_movimiento(
    movimiento_id: int,
    session: Session = Depends(obtener_session),
) -> int | None:
    return empresa_del_movimiento(session, movimiento_id)


def _empresa_de_periodo(
    periodo_id: int,
    session: Session = Depends(obtener_session),
) -> int | None:
    periodo = session.get(Periodo, periodo_id)
    return periodo.empresa_id if periodo is not None else None


def _asegurar_periodo_visible(
    session: Session,
    acceso: Acceso,
    periodo_id: int,
) -> Periodo:
    periodo = session.get(Periodo, periodo_id)
    if periodo is None:
        raise HTTPException(status_code=404, detail="No encontramos ese período.")
    if (
        acceso.empresas_visibles is not None
        and periodo.empresa_id not in acceso.empresas_visibles
    ):
        raise HTTPException(status_code=404, detail="No encontramos ese período.")
    return periodo


def _asegurar_fuente_visible(
    session: Session,
    acceso: Acceso,
    fuente_id: int,
) -> int:
    empresa_id = empresa_de_fuente(session, fuente_id)
    if empresa_id is None:
        raise HTTPException(status_code=404, detail="No encontramos esa fuente.")
    if (
        acceso.empresas_visibles is not None
        and empresa_id not in acceso.empresas_visibles
    ):
        raise HTTPException(status_code=404, detail="No encontramos esa fuente.")
    return empresa_id


def _asegurar_regla_visible(
    session: Session,
    acceso: Acceso,
    regla: ReglaCategorizacion | None,
) -> int | None:
    if regla is None:
        raise HTTPException(status_code=404, detail="No encontramos esa regla.")
    if regla.fuente_id is None:
        if acceso.alcance is not Alcance.TODAS:
            raise HTTPException(status_code=404, detail="No encontramos esa regla.")
        return None
    return _asegurar_fuente_visible(session, acceso, regla.fuente_id)


class CategorizarEntrada(BaseModel):
    tipo: str | None = None
    unidad_negocio: str | None = None
    categoria: str | None = None
    empresa: str | None = None
    tercero: str | None = None
    modalidad: str | None = None
    fijo_variable: str | None = None
    ciudad: str | None = None

    def cambios(self) -> dict[str, str | None]:
        return {
            campo: getattr(self, campo)
            for campo in CAMPOS_CATEGORIA
            if campo in self.model_fields_set
        }


class CategorizarLoteEntrada(CategorizarEntrada):
    movimientos: list[int] = Field(min_length=1, max_length=500)


class RecategorizarEntrada(BaseModel):
    periodo_id: int
    motor_slug: str = Field(min_length=1, max_length=100)
    fuente_id: int | None = None


class ReglaEntrada(BaseModel):
    motor_slug: str = Field(min_length=1, max_length=100)
    fuente_id: int | None = None
    patron: str = Field(min_length=1)
    tipo_match: str
    prioridad: int = 100
    condiciones: dict[str, object] = Field(default_factory=dict)
    tipo: str | None = None
    unidad_negocio: str | None = None
    categoria: str | None = None
    empresa: str | None = None
    tercero: str | None = None
    modalidad: str | None = None
    fijo_variable: str | None = None
    ciudad: str | None = None
    requiere_revision: bool = False
    activa: bool = True
    origen: str | None = "MANUAL"


class ReglaEdicion(BaseModel):
    patron: str | None = None
    tipo_match: str | None = None
    prioridad: int | None = None
    condiciones: dict[str, object] | None = None
    tipo: str | None = None
    unidad_negocio: str | None = None
    categoria: str | None = None
    empresa: str | None = None
    tercero: str | None = None
    modalidad: str | None = None
    fijo_variable: str | None = None
    ciudad: str | None = None
    requiere_revision: bool | None = None
    activa: bool | None = None
    origen: str | None = None


class ImportarWalletsEntrada(BaseModel):
    fuente_id: int
    motor_slug: str = "conciliacion_wallets"


class ReaplicarReglaEntrada(BaseModel):
    periodo_id: int
    fuente_id: int | None = None


@router.get("/movimientos")
def consultar_movimientos(
    periodo: int | None = None,
    fuente: int | None = None,
    estado_categoria: str | None = None,
    categoria: str | None = None,
    q: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    acceso: Acceso = Depends(requiere("conciliacion.ver")),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    if estado_categoria is not None and estado_categoria not in ESTADOS_CATEGORIA:
        raise HTTPException(
            status_code=422,
            detail="estado_categoria debe ser AUTO, REVISAR, PENDIENTE o MANUAL.",
        )
    items = listar_movimientos(
        session,
        empresas_visibles=acceso.empresas_visibles,
        periodo_id=periodo,
        fuente_id=fuente,
        estado_categoria=estado_categoria,
        categoria=categoria,
        q=q,
        offset=offset,
        limite=limit,
    )
    return {
        "offset": offset,
        "limit": limit,
        "items": [movimiento_como_dict(item) for item in items],
    }


@router.patch("/movimientos/{movimiento_id}")
def categorizar_movimiento(
    movimiento_id: int,
    datos: CategorizarEntrada,
    acceso: Acceso = Depends(
        requiere("movimientos.categorizar", empresa_de=_empresa_de_movimiento)
    ),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    cambios = datos.cambios()
    if not cambios:
        raise HTTPException(
            status_code=422,
            detail="Indica al menos una dimensión para categorizar el movimiento.",
        )
    movimiento = session.get(Movimiento, movimiento_id)
    try:
        sugerencia = categorizar_manual(
            session,
            movimiento,
            cambios=cambios,
            usuario_id=acceso.usuario.id,
            ip=acceso.ip,
        )
        session.commit()
        session.refresh(movimiento)
    except PeriodoCerradoError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "movimiento": movimiento_como_dict(movimiento),
        "sugerencia_regla": sugerencia,
        "nota": "La sugerencia no se crea automáticamente; la decisión queda en el usuario.",
    }


@router.post("/movimientos/lote")
def categorizar_movimientos_lote(
    datos: CategorizarLoteEntrada,
    acceso: Acceso = Depends(requiere("movimientos.categorizar")),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    cambios = datos.cambios()
    cambios.pop("movimientos", None)
    if not cambios:
        raise HTTPException(
            status_code=422,
            detail="Indica al menos una dimensión para categorizar los movimientos.",
        )

    movimientos = tuple(
        session.scalars(
            select(Movimiento).where(Movimiento.id.in_(datos.movimientos))
        )
    )
    if len(movimientos) != len(set(datos.movimientos)):
        raise HTTPException(status_code=404, detail="No encontramos todos los movimientos.")

    for movimiento in movimientos:
        empresa_id = empresa_del_movimiento(session, movimiento.id)
        if (
            empresa_id is None
            or (
                acceso.empresas_visibles is not None
                and empresa_id not in acceso.empresas_visibles
            )
        ):
            raise HTTPException(status_code=404, detail="No encontramos todos los movimientos.")

    try:
        for movimiento in movimientos:
            categorizar_manual(
                session,
                movimiento,
                cambios=cambios,
                usuario_id=acceso.usuario.id,
                ip=acceso.ip,
            )
        session.commit()
    except PeriodoCerradoError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        "actualizados": len(movimientos),
        "ids": sorted(movimiento.id for movimiento in movimientos),
    }


@router.post("/movimientos/recategorizar")
def recategorizar(
    datos: RecategorizarEntrada,
    acceso: Acceso = Depends(requiere("movimientos.categorizar")),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    periodo = _asegurar_periodo_visible(session, acceso, datos.periodo_id)
    if datos.fuente_id is not None:
        empresa_fuente = _asegurar_fuente_visible(session, acceso, datos.fuente_id)
        if periodo is None or empresa_fuente != periodo.empresa_id:
            raise HTTPException(
                status_code=422,
                detail="La fuente y el período deben pertenecer a la misma empresa.",
            )
    try:
        resumen = recategorizar_periodo(
            session,
            periodo_id=datos.periodo_id,
            motor_slug=datos.motor_slug,
            fuente_id=datos.fuente_id,
        )
        registrar_auditoria(
            session,
            usuario_id=acceso.usuario.id,
            empresa_id=periodo.empresa_id,
            accion="movimientos.recategorizar",
            entidad="periodo",
            entidad_id=datos.periodo_id,
            despues={"motor_slug": datos.motor_slug, **resumen},
            ip=acceso.ip,
        )
        session.commit()
    except PeriodoCerradoError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return resumen


@router.get("/reglas")
def consultar_reglas(
    motor: str | None = None,
    fuente: int | None = None,
    acceso: Acceso = Depends(requiere("parametros.ver")),
    session: Session = Depends(obtener_session),
) -> list[dict[str, object]]:
    statement = (
        select(ReglaCategorizacion)
        .outerjoin(Fuente, Fuente.id == ReglaCategorizacion.fuente_id)
        .order_by(
            ReglaCategorizacion.motor_slug,
            ReglaCategorizacion.prioridad,
            ReglaCategorizacion.id,
        )
    )
    if acceso.empresas_visibles is not None:
        statement = statement.where(
            or_(
                ReglaCategorizacion.fuente_id.is_(None),
                Fuente.empresa_id.in_(acceso.empresas_visibles),
            )
        )
    if motor:
        statement = statement.where(ReglaCategorizacion.motor_slug == motor)
    if fuente is not None:
        _asegurar_fuente_visible(session, acceso, fuente)
        statement = statement.where(
            or_(
                ReglaCategorizacion.fuente_id.is_(None),
                ReglaCategorizacion.fuente_id == fuente,
            )
        )
    return [regla_como_dict(regla) for regla in session.scalars(statement)]


@router.post("/reglas", status_code=201)
def crear_regla(
    datos: ReglaEntrada,
    acceso: Acceso = Depends(requiere("reglas.crear")),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    tipo_match = datos.tipo_match.upper()
    if tipo_match not in TIPOS_MATCH:
        raise HTTPException(
            status_code=422,
            detail="tipo_match debe ser EXACTO, EMPIEZA_CON, CONTIENE o REGEX.",
        )

    empresa_id = None
    if datos.fuente_id is None:
        if acceso.alcance is not Alcance.TODAS:
            raise HTTPException(
                status_code=403,
                detail="Solo un rol con alcance global puede crear reglas sin fuente.",
            )
    else:
        empresa_id = _asegurar_fuente_visible(session, acceso, datos.fuente_id)

    regla = ReglaCategorizacion(
        **datos.model_dump(exclude={"tipo_match"}),
        tipo_match=tipo_match,
        patron=datos.patron.strip(),
        creado_por=acceso.usuario.id,
    )
    session.add(regla)
    session.flush()
    registrar_auditoria(
        session,
        usuario_id=acceso.usuario.id,
        empresa_id=empresa_id,
        accion="regla_categorizacion.crear",
        entidad="regla_categorizacion",
        entidad_id=regla.id,
        despues=regla_como_dict(regla),
        ip=acceso.ip,
    )
    session.commit()
    session.refresh(regla)
    return regla_como_dict(regla)


@router.patch("/reglas/{regla_id}")
def editar_regla(
    regla_id: int,
    datos: ReglaEdicion,
    acceso: Acceso = Depends(requiere("reglas.crear")),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    regla = session.get(ReglaCategorizacion, regla_id)
    empresa_id = _asegurar_regla_visible(session, acceso, regla)
    cambios = datos.model_dump(exclude_unset=True)
    if not cambios:
        raise HTTPException(status_code=422, detail="No hay cambios para aplicar.")
    if "tipo_match" in cambios and cambios["tipo_match"] is not None:
        cambios["tipo_match"] = cambios["tipo_match"].upper()
        if cambios["tipo_match"] not in TIPOS_MATCH:
            raise HTTPException(
                status_code=422,
                detail="tipo_match debe ser EXACTO, EMPIEZA_CON, CONTIENE o REGEX.",
            )
    if "patron" in cambios and cambios["patron"] is not None:
        cambios["patron"] = cambios["patron"].strip()
        if not cambios["patron"]:
            raise HTTPException(status_code=422, detail="patron no puede quedar vacío.")

    antes = regla_como_dict(regla)
    for campo, valor in cambios.items():
        setattr(regla, campo, valor)
    registrar_auditoria(
        session,
        usuario_id=acceso.usuario.id,
        empresa_id=empresa_id,
        accion="regla_categorizacion.editar",
        entidad="regla_categorizacion",
        entidad_id=regla.id,
        antes=antes,
        despues=regla_como_dict(regla),
        ip=acceso.ip,
    )
    session.commit()
    session.refresh(regla)
    return regla_como_dict(regla)


@router.post("/reglas/importar")
def importar_catalogo_wallets(
    datos: ImportarWalletsEntrada,
    acceso: Acceso = Depends(requiere("reglas.crear")),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    empresa_id = _asegurar_fuente_visible(session, acceso, datos.fuente_id)
    ruta = (
        Path(__file__).resolve().parents[3]
        / "docs"
        / "motores"
        / "conciliacion_wallets"
        / "catalogo_conceptos_wallets.json"
    )
    catalogo = json.loads(ruta.read_text(encoding="utf-8"))
    importadas = reglas_desde_catalogo_wallets(
        catalogo,
        motor_slug=datos.motor_slug,
        fuente_id=datos.fuente_id,
    )

    creadas: list[int] = []
    omitidas = 0
    for importada in importadas:
        existente = session.scalar(
            select(ReglaCategorizacion.id).where(
                ReglaCategorizacion.motor_slug == importada.motor_slug,
                ReglaCategorizacion.fuente_id == importada.fuente_id,
                ReglaCategorizacion.patron == importada.patron,
                ReglaCategorizacion.tipo_match == importada.tipo_match,
                ReglaCategorizacion.prioridad == importada.prioridad,
            )
        )
        if existente is not None:
            omitidas += 1
            continue
        regla = ReglaCategorizacion(
            **asdict(importada),
            creado_por=acceso.usuario.id,
        )
        session.add(regla)
        session.flush()
        creadas.append(regla.id)

    registrar_auditoria(
        session,
        usuario_id=acceso.usuario.id,
        empresa_id=empresa_id,
        accion="reglas_categorizacion.importar_wallets",
        entidad="fuente",
        entidad_id=datos.fuente_id,
        despues={
            "motor_slug": datos.motor_slug,
            "creadas": len(creadas),
            "omitidas": omitidas,
        },
        ip=acceso.ip,
    )
    session.commit()
    return {
        "creadas": len(creadas),
        "omitidas": omitidas,
        "ids_creados": creadas,
        "fuente_id": datos.fuente_id,
        "motor_slug": datos.motor_slug,
    }


@router.post("/reglas/{regla_id}/reaplicar")
def reaplicar(
    regla_id: int,
    datos: ReaplicarReglaEntrada,
    acceso: Acceso = Depends(requiere("reglas.crear")),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    regla = session.get(ReglaCategorizacion, regla_id)
    _asegurar_regla_visible(session, acceso, regla)
    periodo = _asegurar_periodo_visible(session, acceso, datos.periodo_id)

    if regla.fuente_id is not None:
        empresa_fuente = empresa_de_fuente(session, regla.fuente_id)
        if periodo is None or empresa_fuente != periodo.empresa_id:
            raise HTTPException(
                status_code=422,
                detail="La regla y el período deben pertenecer a la misma empresa.",
            )
    elif datos.fuente_id is not None:
        empresa_fuente = _asegurar_fuente_visible(session, acceso, datos.fuente_id)
        if periodo is None or empresa_fuente != periodo.empresa_id:
            raise HTTPException(
                status_code=422,
                detail="La fuente y el período deben pertenecer a la misma empresa.",
            )

    try:
        resumen = reaplicar_regla(
            session,
            regla,
            periodo_id=datos.periodo_id,
            fuente_id=datos.fuente_id,
        )
        registrar_auditoria(
            session,
            usuario_id=acceso.usuario.id,
            empresa_id=periodo.empresa_id if periodo else None,
            accion="regla_categorizacion.reaplicar",
            entidad="regla_categorizacion",
            entidad_id=regla.id,
            despues={"periodo_id": datos.periodo_id, **resumen},
            ip=acceso.ip,
        )
        session.commit()
    except PeriodoCerradoError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return resumen
