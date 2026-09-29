from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.dependencias import usuario_vigente
from app.core.auth.service import empresas_del_usuario
from app.core.hallazgos import Hallazgo
from app.core.periodos import Periodo
from app.core.permisos import permisos_efectivos
from app.core.session import obtener_session
from app.core.usuarios import Usuario
from app.integrations.google_sheets.service import (
    ejecutar_refresco_reclamado,
    estado_como_dict,
    obtener_estado,
    reclamar_refresco_si_corresponde,
)
from app.motores.cartera_ocs.bandeja import listar_comprobantes_pendientes
from app.motores.cartera_ocs.snapshot_model import CarteraSnapshot
from app.motores.compras_supply_chain.atencion import evaluar_puntos_atencion
from app.motores.compras_supply_chain.contrato import DiagnosticoEsquema
from app.motores.compras_supply_chain.dominio import LineaCompra
from app.motores.compras_supply_chain.ejecutivo import resumen_ejecutivo
from app.motores.compras_supply_chain.kpis import calcular_familias_monetarias
from app.motores.compras_supply_chain.model import CompraSnapshot, CompraSnapshotLinea


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


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


def _ultimo_snapshot_cartera(
    session: Session,
    *,
    empresa_id: int,
) -> CarteraSnapshot | None:
    return session.scalar(
        select(CarteraSnapshot)
        .where(CarteraSnapshot.empresa_id == empresa_id)
        .order_by(
            CarteraSnapshot.guardado_en.desc(),
            CarteraSnapshot.id.desc(),
        )
        .limit(1)
    )


def _ultimo_snapshot_compras(
    session: Session,
    *,
    empresa_id: int,
) -> CompraSnapshot | None:
    return session.scalar(
        select(CompraSnapshot)
        .where(CompraSnapshot.empresa_id == empresa_id)
        .order_by(
            CompraSnapshot.guardado_en.desc(),
            CompraSnapshot.id.desc(),
        )
        .limit(1)
    )


def _lineas_compras_desde_snapshot(
    session: Session,
    *,
    snapshot_id: int,
) -> tuple[LineaCompra, ...]:
    filas = session.scalars(
        select(CompraSnapshotLinea)
        .where(CompraSnapshotLinea.snapshot_id == snapshot_id)
        .order_by(CompraSnapshotLinea.id)
    )
    return tuple(
        LineaCompra(**fila.normalizado)
        for fila in filas
        if fila.normalizado
    )


def _diagnosticos_compras_desde_snapshot(
    snapshot: CompraSnapshot,
) -> tuple[DiagnosticoEsquema, ...]:
    resultado: list[DiagnosticoEsquema] = []
    for item in snapshot.diagnosticos:
        resultado.append(
            DiagnosticoEsquema(
                pais=str(item.get("pais") or ""),
                rango=str(item.get("rango") or ""),
                encabezados=tuple(item.get("encabezados") or ()),
                filas_datos=int(item.get("filas_datos") or 0),
                campos_reconocidos=tuple(item.get("campos_reconocidos") or ()),
                campos_criticos_faltantes=tuple(
                    item.get("campos_criticos_faltantes") or ()
                ),
                campos_esperados_faltantes=tuple(
                    item.get("campos_esperados_faltantes") or ()
                ),
                encabezados_duplicados=tuple(
                    item.get("encabezados_duplicados") or ()
                ),
                encabezados_no_consumidos=tuple(
                    item.get("encabezados_no_consumidos") or ()
                ),
            )
        )
    return tuple(resultado)


def _leer_cartera(
    *,
    empresa_id: int,
    session: Session,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    snapshot = _ultimo_snapshot_cartera(session, empresa_id=empresa_id)
    pendientes = listar_comprobantes_pendientes(session, empresa_id=empresa_id)

    resumen: dict[str, object] = {
        "operaciones": snapshot.operaciones if snapshot else None,
        "registros_mora": snapshot.registros_mora if snapshot else None,
        "proyecciones": snapshot.proyecciones if snapshot else None,
        "comprobantes_pendientes": len(pendientes),
    }

    fuentes: dict[str, dict[str, object]] = {}
    if snapshot is None:
        for codigo in ("operaciones", "mora", "proyeccion"):
            fuentes[codigo] = {"estado": "SIN_SNAPSHOT"}
    else:
        for diagnostico in snapshot.diagnosticos:
            codigo = str(diagnostico.get("tipo") or "").lower()
            if not codigo:
                continue
            configurado = diagnostico.get("configurado") is not False
            valido = diagnostico.get("valido") is True
            if valido:
                estado = "DISPONIBLE"
            elif not configurado:
                estado = "NO_CONFIGURADO"
            else:
                estado = "DEGRADADO"
            fuentes[codigo] = {
                "estado": estado,
                "registros": int(diagnostico.get("filas_datos") or 0),
            }

    atencion = [
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
        for pendiente in pendientes[:5]
    ]

    return (
        {
            "codigo": "cartera",
            "titulo": "Cartera",
            "disponible": snapshot is not None or bool(pendientes),
            "resumen": resumen,
            "estado_datos": fuentes,
            "actualizado_en": (
                snapshot.cargado_en.isoformat()
                if snapshot is not None
                else None
            ),
            "snapshot_id": snapshot.id if snapshot is not None else None,
            "accion": {"vista": "cartera", "texto": "Ver cartera"},
        },
        atencion,
    )


def _leer_compras(
    *,
    empresa_id: int,
    session: Session,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    snapshot = _ultimo_snapshot_compras(session, empresa_id=empresa_id)
    if snapshot is None:
        return (
            {
                "codigo": "compras",
                "titulo": "Compras / Supply Chain",
                "disponible": False,
                "resumen": {},
                "estado_datos": {
                    "estado": "SIN_SNAPSHOT",
                    "detalle": (
                        "Todavía no existe una captura persistida de Compras."
                    ),
                },
                "actualizado_en": None,
                "snapshot_id": None,
                "accion": {"vista": "compras", "texto": "Ver compras"},
            },
            [],
        )

    if not snapshot.esquema_valido:
        return (
            {
                "codigo": "compras",
                "titulo": "Compras / Supply Chain",
                "disponible": False,
                "resumen": {},
                "estado_datos": {
                    "estado": "DEGRADADO",
                    "modo_fuente": snapshot.modo_fuente,
                    "cargado_en": snapshot.cargado_en.isoformat(),
                    "esquema_valido": False,
                },
                "actualizado_en": snapshot.cargado_en.isoformat(),
                "snapshot_id": snapshot.id,
                "accion": {"vista": "compras", "texto": "Ver compras"},
            },
            [],
        )

    lineas = _lineas_compras_desde_snapshot(
        session,
        snapshot_id=snapshot.id,
    )
    diagnosticos = _diagnosticos_compras_desde_snapshot(snapshot)
    estructural = resumen_ejecutivo(lineas)
    familias = {
        item.familia.codigo: item
        for item in calcular_familias_monetarias(
            lineas,
            diagnosticos,
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
                "modo_fuente": snapshot.modo_fuente,
                "cargado_en": snapshot.cargado_en.isoformat(),
                "esquema_valido": snapshot.esquema_valido,
            },
            "actualizado_en": snapshot.cargado_en.isoformat(),
            "snapshot_id": snapshot.id,
            "accion": {"vista": "compras", "texto": "Ver compras"},
        },
        atencion,
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


def _versiones(
    session: Session,
    *,
    empresa_id: int,
) -> dict[str, int | None]:
    cartera = _ultimo_snapshot_cartera(session, empresa_id=empresa_id)
    compras = _ultimo_snapshot_compras(session, empresa_id=empresa_id)
    return {
        "cartera": cartera.id if cartera is not None else None,
        "compras": compras.id if compras is not None else None,
    }


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
        modulo, items = _leer_compras(
            empresa_id=empresa_id,
            session=session,
        )
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
        "versiones": _versiones(session, empresa_id=empresa_id),
        "modulos": modulos,
        "atencion": atencion[:12],
        "nota": (
            "Inicio lee snapshots persistidos; no consulta Google Sheets al abrir "
            "o recargar la página. No calcula scores, rankings ni severidades nuevas."
        ),
    }


@router.get("/version")
def dashboard_version(
    empresa_id: int,
    background_tasks: BackgroundTasks,
    usuario: Usuario = Depends(usuario_vigente),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    _empresa_visible(session, usuario, empresa_id)
    permisos = permisos_efectivos(usuario.rol)

    modulos = []
    if "cartera.ver" in permisos:
        modulos.append("cartera")
    if "compras.ver" in permisos:
        modulos.append("compras")

    reclamos: list[tuple[str, datetime]] = []
    for modulo in modulos:
        corte = reclamar_refresco_si_corresponde(
            session,
            empresa_id=empresa_id,
            modulo=modulo,
        )
        if corte is not None:
            reclamos.append((modulo, corte))
    session.commit()

    for modulo, corte in reclamos:
        background_tasks.add_task(
            ejecutar_refresco_reclamado,
            empresa_id=empresa_id,
            modulo=modulo,
            corte_iso=corte.isoformat(),
        )

    estados = {
        modulo: estado_como_dict(
            obtener_estado(
                session,
                empresa_id=empresa_id,
                modulo=modulo,
            )
        )
        for modulo in modulos
    }

    return {
        "empresa_id": empresa_id,
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "versiones": _versiones(session, empresa_id=empresa_id),
        "fuentes": estados,
    }
