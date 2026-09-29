from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.auditoria.service import registrar_auditoria
from app.core.session import crear_session
from app.motores.cartera_ocs.snapshots import (
    capturar_snapshot_cartera_desde_entorno,
    guardar_snapshot_cartera,
)
from app.motores.compras_supply_chain.api import obtener_fuente_compras
from app.motores.compras_supply_chain.persistencia import guardar_snapshot

from .model import SourceRefreshState


MODULOS_SOPORTADOS = frozenset({"cartera", "compras"})


def _segundos(nombre: str, defecto: int) -> int:
    crudo = os.getenv(nombre, str(defecto)).strip()
    try:
        valor = int(crudo)
    except ValueError as exc:
        raise RuntimeError(f"{nombre} debe ser entero.") from exc
    if valor < 0:
        raise RuntimeError(f"{nombre} no puede ser negativo.")
    return valor


def registrar_cambio(
    session: Session,
    *,
    empresa_id: int,
    modulo: str,
    ahora: datetime | None = None,
) -> SourceRefreshState:
    """Registra un cambio sin leer Google; múltiples eventos se coalescen."""
    if modulo not in MODULOS_SOPORTADOS:
        raise ValueError(f"Módulo no soportado: {modulo}.")

    ahora = ahora or datetime.now(timezone.utc)
    tabla = SourceRefreshState.__table__
    stmt = pg_insert(tabla).values(
        empresa_id=empresa_id,
        modulo=modulo,
        estado="PENDING",
        first_event_at=ahora,
        last_event_at=ahora,
        event_count=1,
        last_error=None,
        updated_at=ahora,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_source_refresh_states_empresa_modulo",
        set_={
            "estado": "PENDING",
            "first_event_at": case(
                (
                    tabla.c.estado.in_(("IDLE", "ERROR")),
                    ahora,
                ),
                (
                    tabla.c.first_event_at.is_(None),
                    ahora,
                ),
                else_=tabla.c.first_event_at,
            ),
            "last_event_at": ahora,
            "event_count": tabla.c.event_count + 1,
            "last_error": None,
            "updated_at": ahora,
        },
    )
    session.execute(stmt)
    session.flush()
    estado = session.scalar(
        select(SourceRefreshState).where(
            SourceRefreshState.empresa_id == empresa_id,
            SourceRefreshState.modulo == modulo,
        )
    )
    assert estado is not None
    return estado


def obtener_estado(
    session: Session,
    *,
    empresa_id: int,
    modulo: str,
) -> SourceRefreshState | None:
    return session.scalar(
        select(SourceRefreshState).where(
            SourceRefreshState.empresa_id == empresa_id,
            SourceRefreshState.modulo == modulo,
        )
    )


def reclamar_refresco_si_corresponde(
    session: Session,
    *,
    empresa_id: int,
    modulo: str,
    ahora: datetime | None = None,
) -> datetime | None:
    """Marca REFRESHING solo cuando venció quiet-period o max-wait.

    Devuelve el último evento incluido en este refresco. El caller puede ejecutar
    la lectura de Google después de responder al navegador.
    """
    ahora = ahora or datetime.now(timezone.utc)
    estado = session.scalar(
        select(SourceRefreshState)
        .where(
            SourceRefreshState.empresa_id == empresa_id,
            SourceRefreshState.modulo == modulo,
        )
        .with_for_update()
    )
    if estado is None or estado.estado != "PENDING" or estado.last_event_at is None:
        return None

    primero = estado.first_event_at or estado.last_event_at
    debounce = _segundos("GOOGLE_SHEETS_DEBOUNCE_SECONDS", 15)
    espera_maxima = _segundos("GOOGLE_SHEETS_MAX_WAIT_SECONDS", 60)
    vence_quiet = estado.last_event_at + timedelta(seconds=debounce)
    vence_max = primero + timedelta(seconds=espera_maxima)
    vence = min(vence_quiet, vence_max)

    if ahora < vence:
        return None

    corte = estado.last_event_at
    estado.estado = "REFRESHING"
    estado.updated_at = ahora
    session.flush()
    return corte


def _refrescar_cartera(
    session: Session,
    *,
    empresa_id: int,
) -> tuple[int, bool]:
    snapshot = capturar_snapshot_cartera_desde_entorno(empresa_id=empresa_id)
    persistido, creado = guardar_snapshot_cartera(
        session,
        empresa_id=empresa_id,
        snapshot=snapshot,
    )
    if creado:
        registrar_auditoria(
            session,
            usuario_id=None,
            empresa_id=empresa_id,
            accion="cartera.snapshot_automatico",
            entidad="cartera_snapshot",
            entidad_id=persistido.id,
            despues={
                "contenido_hash": persistido.contenido_hash,
                "filas": persistido.filas,
                "operaciones": persistido.operaciones,
                "registros_mora": persistido.registros_mora,
                "proyecciones": persistido.proyecciones,
            },
        )
    return persistido.id, creado


def _refrescar_compras(
    session: Session,
    *,
    empresa_id: int,
) -> tuple[int, bool]:
    fuente = obtener_fuente_compras()
    snapshot = fuente.obtener_snapshot(
        empresa_id=empresa_id,
        forzar_lectura=True,
    )
    persistido, creado = guardar_snapshot(
        session,
        empresa_id=empresa_id,
        spreadsheet_id=fuente.configuracion.spreadsheet_id,
        modo_fuente=fuente.configuracion.modo_fuente,
        rangos_por_pais=fuente.configuracion.rangos_por_pais,
        snapshot=snapshot,
    )
    if creado:
        registrar_auditoria(
            session,
            usuario_id=None,
            empresa_id=empresa_id,
            accion="compras.snapshot_automatico",
            entidad="compras_snapshot",
            entidad_id=persistido.id,
            despues={
                "contenido_hash": persistido.contenido_hash,
                "lineas": persistido.lineas,
                "esquema_valido": persistido.esquema_valido,
            },
        )
    return persistido.id, creado


def _ejecutar_refresco(
    session: Session,
    *,
    empresa_id: int,
    modulo: str,
) -> tuple[int, bool]:
    if modulo == "cartera":
        return _refrescar_cartera(session, empresa_id=empresa_id)
    if modulo == "compras":
        return _refrescar_compras(session, empresa_id=empresa_id)
    raise ValueError(f"Módulo no soportado: {modulo}.")


def ejecutar_refresco_reclamado(
    *,
    empresa_id: int,
    modulo: str,
    corte_iso: str,
) -> None:
    """Background task: refresca una vez y conserva eventos que lleguen durante la lectura."""
    corte = datetime.fromisoformat(corte_iso)
    try:
        with crear_session() as session:
            snapshot_id, creado = _ejecutar_refresco(
                session,
                empresa_id=empresa_id,
                modulo=modulo,
            )
            session.commit()

        with crear_session() as session:
            estado = session.scalar(
                select(SourceRefreshState)
                .where(
                    SourceRefreshState.empresa_id == empresa_id,
                    SourceRefreshState.modulo == modulo,
                )
                .with_for_update()
            )
            if estado is None:
                return
            ahora = datetime.now(timezone.utc)
            estado.processed_through_at = corte
            estado.last_refresh_at = ahora
            estado.last_error = None
            if estado.last_event_at is not None and estado.last_event_at > corte:
                estado.estado = "PENDING"
                estado.first_event_at = estado.last_event_at
            else:
                estado.estado = "IDLE"
                estado.first_event_at = None
            estado.updated_at = ahora
            session.commit()

        _ = snapshot_id, creado
    except Exception as exc:
        with crear_session() as session:
            estado = session.scalar(
                select(SourceRefreshState)
                .where(
                    SourceRefreshState.empresa_id == empresa_id,
                    SourceRefreshState.modulo == modulo,
                )
                .with_for_update()
            )
            if estado is None:
                return
            ahora = datetime.now(timezone.utc)
            estado.last_refresh_at = ahora
            estado.last_error = str(exc)[:4000]
            if estado.last_event_at is not None and estado.last_event_at > corte:
                estado.estado = "PENDING"
                estado.first_event_at = estado.last_event_at
            else:
                estado.estado = "ERROR"
                estado.first_event_at = None
            estado.updated_at = ahora
            session.commit()


def estado_como_dict(estado: SourceRefreshState | None) -> dict[str, object]:
    if estado is None:
        return {
            "estado": "IDLE",
            "eventos": 0,
            "ultimo_evento": None,
            "ultimo_refresco": None,
            "error": None,
        }
    return {
        "estado": estado.estado,
        "eventos": estado.event_count,
        "ultimo_evento": (
            estado.last_event_at.isoformat()
            if estado.last_event_at is not None
            else None
        ),
        "ultimo_refresco": (
            estado.last_refresh_at.isoformat()
            if estado.last_refresh_at is not None
            else None
        ),
        "error": estado.last_error,
    }
