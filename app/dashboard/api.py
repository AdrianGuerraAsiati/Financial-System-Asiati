from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.dependencias import usuario_vigente
from app.core.auth.service import empresas_del_usuario
from app.core.hallazgos import Hallazgo
from app.core.periodos import Periodo
from app.core.permisos import permisos_efectivos
from app.core.session import obtener_session
from app.core.usuarios import Usuario
from app.motores.cartera_ocs.api import (
    obtener_fuente_mora,
    obtener_fuente_operaciones,
    obtener_fuente_proyeccion,
)
from app.motores.cartera_ocs.bandeja import listar_comprobantes_pendientes
from app.motores.cartera_ocs.mora import listar_mora
from app.motores.cartera_ocs.proyeccion import listar_proyeccion
from app.motores.cartera_ocs.consultas import listar_operaciones
from app.motores.compras_supply_chain.api import obtener_fuente_compras
from app.motores.compras_supply_chain.atencion import evaluar_puntos_atencion
from app.motores.compras_supply_chain.ejecutivo import resumen_ejecutivo
from app.motores.compras_supply_chain.google_sheets import (
    ConfiguracionComprasGoogleSheetsError,
    EsquemaComprasInvalidoError,
    LecturaComprasGoogleSheetsError,
)
from app.motores.compras_supply_chain.kpis import calcular_familias_monetarias


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _error_texto(exc: Exception) -> str:
    detail = getattr(exc, "detail", None)
    return str(detail or exc)


def _empresa_visible(
    session: Session,
    usuario: Usuario,
    empresa_id: int,
):
    empresas = empresas_del_usuario(session, usuario)
    empresa = next((item for item in empresas if item.id == empresa_id), None)
    if empresa is None:
        raise HTTPException(status_code=404, detail="No encontramos esa empresa.")
    return empresa


def _leer_cartera(
    *,
    empresa_id: int,
    session: Session,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    fuentes: dict[str, dict[str, object]] = {}
    resumen: dict[str, object] = {
        "operaciones": None,
        "registros_mora": None,
        "proyecciones": None,
        "comprobantes_pendientes": 0,
    }
    atencion: list[dict[str, object]] = []

    lectores = (
        (
            "operaciones",
            obtener_fuente_operaciones,
            lambda fuente: listar_operaciones(fuente, empresa_id=empresa_id),
        ),
        (
            "mora",
            obtener_fuente_mora,
            lambda fuente: listar_mora(fuente, empresa_id=empresa_id),
        ),
        (
            "proyeccion",
            obtener_fuente_proyeccion,
            lambda fuente: listar_proyeccion(fuente, empresa_id=empresa_id),
        ),
    )

    for codigo, construir, leer in lectores:
        try:
            registros = tuple(leer(construir()))
            fuentes[codigo] = {
                "estado": "DISPONIBLE",
                "registros": len(registros),
            }
            if codigo == "operaciones":
                resumen["operaciones"] = len(registros)
            elif codigo == "mora":
                resumen["registros_mora"] = len(registros)
            else:
                resumen["proyecciones"] = len(registros)
        except Exception as exc:
            fuentes[codigo] = {
                "estado": "NO_DISPONIBLE",
                "detalle": _error_texto(exc),
            }

    pendientes = listar_comprobantes_pendientes(session, empresa_id=empresa_id)
    resumen["comprobantes_pendientes"] = len(pendientes)
    for pendiente in pendientes[:5]:
        atencion.append(
            {
                "modulo": "cartera",
                "codigo": "COMPROBANTE_PENDIENTE",
                "categoria": "PENDIENTE",
                "titulo": "Comprobante pendiente de auditoría",
                "descripcion": (
                    f"{pendiente.cliente} · OC {pendiente.oc} · "
                    f"{pendiente.nombre_archivo}"
                ),
                "referencia": pendiente.oc,
                "url_destino": "cartera",
            }
        )

    disponible = any(
        fuente["estado"] == "DISPONIBLE" for fuente in fuentes.values()
    ) or bool(pendientes)

    return (
        {
            "codigo": "cartera",
            "titulo": "Cartera",
            "disponible": disponible,
            "resumen": resumen,
            "estado_datos": fuentes,
            "accion": {"vista": "cartera", "texto": "Ver cartera"},
        },
        atencion,
    )


def _leer_compras(
    *,
    empresa_id: int,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    try:
        fuente = obtener_fuente_compras()
        snapshot = fuente.obtener_snapshot(empresa_id=empresa_id)
        if not snapshot.esquema_valido:
            raise EsquemaComprasInvalidoError(
                "El contrato de la fuente de Compras está degradado."
            )
        lineas = snapshot.lineas
        estructural = resumen_ejecutivo(lineas)
        familias = {
            item.familia.codigo: item
            for item in calcular_familias_monetarias(
                lineas,
                snapshot.diagnosticos,
            )
        }
        costo = familias.get("costo_compra")
        ddp = familias.get("valor_comercial_ddp")
        puntos = evaluar_puntos_atencion(lineas)

        atencion: list[dict[str, object]] = []
        for punto in puntos[:6]:
            muestra = punto.muestras[0] if punto.muestras else None
            atencion.append(
                {
                    "modulo": "compras",
                    "codigo": punto.codigo,
                    "categoria": punto.categoria,
                    "titulo": punto.titulo,
                    "descripcion": (
                        f"{punto.cantidad} observación(es). "
                        f"{punto.descripcion}"
                    ),
                    "referencia": (
                        muestra.numero_oc
                        if muestra and muestra.numero_oc
                        else None
                    ),
                    "url_destino": "compras",
                }
            )

        return (
            {
                "codigo": "compras",
                "titulo": "Compras / Supply Chain",
                "disponible": True,
                "resumen": {
                    "costo_compra_usd": (
                        costo.activo.como_dict()["monto_usd"]
                        if costo and costo.disponible and costo.activo
                        else None
                    ),
                    "valor_comercial_ddp_usd": (
                        ddp.activo.como_dict()["monto_usd"]
                        if ddp and ddp.disponible and ddp.activo
                        else None
                    ),
                    "ocs_poblacion_actual": estructural[
                        "ocs_con_al_menos_una_linea_en_poblacion_actual"
                    ],
                    "puntos_atencion": estructural["puntos_atencion_total"],
                },
                "estado_datos": {
                    "estado": "DISPONIBLE",
                    "modo_fuente": fuente.configuracion.modo_fuente,
                    "cargado_en": snapshot.cargado_en.isoformat(),
                    "esquema_valido": snapshot.esquema_valido,
                },
                "accion": {"vista": "compras", "texto": "Ver compras"},
            },
            atencion,
        )
    except (
        ConfiguracionComprasGoogleSheetsError,
        EsquemaComprasInvalidoError,
        LecturaComprasGoogleSheetsError,
        HTTPException,
    ) as exc:
        return (
            {
                "codigo": "compras",
                "titulo": "Compras / Supply Chain",
                "disponible": False,
                "resumen": {},
                "estado_datos": {
                    "estado": "NO_DISPONIBLE",
                    "detalle": _error_texto(exc),
                },
                "accion": {"vista": "compras", "texto": "Ver compras"},
            },
            [],
        )


def _leer_conciliacion(
    *,
    empresa_id: int,
    session: Session,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    periodo = session.scalar(
        select(Periodo)
        .where(Periodo.empresa_id == empresa_id)
        .order_by(Periodo.fecha_fin.desc(), Periodo.id.desc())
        .limit(1)
    )

    if periodo is None:
        return (
            {
                "codigo": "conciliacion",
                "titulo": "Conciliación",
                "disponible": True,
                "resumen": {
                    "ultimo_periodo": None,
                    "hallazgos_abiertos": 0,
                    "hallazgos_criticos_abiertos": 0,
                },
                "estado_datos": {
                    "estado": "SIN_EJECUCIONES",
                    "detalle": "Todavía no hay períodos para esta empresa.",
                },
                "accion": None,
            },
            [],
        )

    hallazgos = tuple(
        session.scalars(
            select(Hallazgo)
            .where(
                Hallazgo.periodo_id == periodo.id,
                Hallazgo.motor_slug == "conciliacion_wallets",
            )
            .order_by(Hallazgo.id.desc())
        )
    )
    abiertos = tuple(
        item
        for item in hallazgos
        if not item.resuelto and item.estado not in {"resuelto", "cerrado"}
    )
    criticos = tuple(item for item in abiertos if item.critico)

    atencion = [
        {
            "modulo": "conciliacion",
            "codigo": hallazgo.codigo_regla or "HALLAZGO",
            "categoria": "DIFERENCIA",
            "titulo": hallazgo.codigo_regla or "Hallazgo de conciliación",
            "descripcion": hallazgo.descripcion or "Requiere revisión.",
            "referencia": str(hallazgo.id),
            "url_destino": None,
        }
        for hallazgo in abiertos[:5]
    ]

    return (
        {
            "codigo": "conciliacion",
            "titulo": "Conciliación",
            "disponible": True,
            "resumen": {
                "ultimo_periodo": {
                    "id": periodo.id,
                    "fecha_inicio": periodo.fecha_inicio.isoformat(),
                    "fecha_fin": periodo.fecha_fin.isoformat(),
                    "cerrado": periodo.cerrado,
                },
                "hallazgos_abiertos": len(abiertos),
                "hallazgos_criticos_abiertos": len(criticos),
            },
            "estado_datos": {
                "estado": "DISPONIBLE",
                "periodo_id": periodo.id,
            },
            "accion": None,
        },
        atencion,
    )


@router.get("/principal")
def dashboard_principal(
    empresa_id: int,
    usuario: Usuario = Depends(usuario_vigente),
    session: Session = Depends(obtener_session),
) -> dict[str, Any]:
    empresa = _empresa_visible(session, usuario, empresa_id)
    permisos = permisos_efectivos(usuario.rol)

    modulos: list[dict[str, object]] = []
    atencion: list[dict[str, object]] = []

    if "cartera.ver" in permisos:
        modulo, items = _leer_cartera(
            empresa_id=empresa_id,
            session=session,
        )
        modulos.append(modulo)
        atencion.extend(items)

    if "compras.ver" in permisos:
        modulo, items = _leer_compras(empresa_id=empresa_id)
        modulos.append(modulo)
        atencion.extend(items)

    if "conciliacion.ver" in permisos:
        modulo, items = _leer_conciliacion(
            empresa_id=empresa_id,
            session=session,
        )
        modulos.append(modulo)
        atencion.extend(items)

    return {
        "empresa": {"id": empresa.id, "nombre": empresa.nombre},
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "modulos": modulos,
        "atencion": atencion[:12],
        "nota": (
            "Inicio resume únicamente módulos visibles para el usuario. "
            "No calcula scores, rankings ni severidades nuevas."
        ),
    }
