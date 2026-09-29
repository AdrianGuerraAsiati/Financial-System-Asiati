from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from .google_sheets import SnapshotCompras
from .model import CompraSnapshot, CompraSnapshotLinea


def _hash_snapshot(
    *,
    spreadsheet_id: str,
    rangos_por_pais: Mapping[str, str],
    snapshot: SnapshotCompras,
) -> str:
    payload = {
        "spreadsheet_id": spreadsheet_id,
        "rangos_por_pais": dict(sorted(rangos_por_pais.items())),
        "diagnosticos": [
            diagnostico.como_dict()
            for diagnostico in snapshot.diagnosticos
        ],
        "filas": [
            {
                "pais": fila.pais,
                "hoja_fuente": fila.hoja_fuente,
                "fila_fuente": fila.fila_fuente,
                "valores": list(fila.valores),
            }
            for fila in snapshot.filas_crudas
        ],
    }
    serializado = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(serializado).hexdigest()


def guardar_snapshot(
    session: Session,
    *,
    empresa_id: int,
    spreadsheet_id: str,
    modo_fuente: str,
    rangos_por_pais: Mapping[str, str],
    snapshot: SnapshotCompras,
) -> tuple[CompraSnapshot, bool]:
    """Persiste una captura inmutable; el mismo contenido no se duplica."""
    contenido_hash = _hash_snapshot(
        spreadsheet_id=spreadsheet_id,
        rangos_por_pais=rangos_por_pais,
        snapshot=snapshot,
    )
    existente = session.scalar(
        select(CompraSnapshot).where(
            CompraSnapshot.empresa_id == empresa_id,
            CompraSnapshot.contenido_hash == contenido_hash,
        )
    )
    if existente is not None:
        return existente, False

    fila_snapshot = CompraSnapshot(
        empresa_id=empresa_id,
        spreadsheet_id=spreadsheet_id,
        modo_fuente=modo_fuente,
        contenido_hash=contenido_hash,
        cargado_en=snapshot.cargado_en,
        lineas=len(snapshot.lineas),
        esquema_valido=snapshot.esquema_valido,
        rangos_por_pais=dict(rangos_por_pais),
        diagnosticos=[
            diagnostico.como_dict()
            for diagnostico in snapshot.diagnosticos
        ],
    )
    session.add(fila_snapshot)
    session.flush()

    normalizadas = {
        (linea.pais, linea.fila_fuente): linea
        for linea in snapshot.lineas
    }
    for fila_cruda in snapshot.filas_crudas:
        linea = normalizadas.get(
            (fila_cruda.pais, fila_cruda.fila_fuente)
        )
        session.add(
            CompraSnapshotLinea(
                snapshot_id=fila_snapshot.id,
                pais=fila_cruda.pais,
                hoja_fuente=fila_cruda.hoja_fuente,
                fila_fuente=fila_cruda.fila_fuente,
                crudo={"valores": list(fila_cruda.valores)},
                normalizado=(
                    linea.como_dict()
                    if linea is not None
                    else {}
                ),
            )
        )

    return fila_snapshot, True


def listar_snapshots(
    session: Session,
    *,
    empresa_id: int,
    limite: int = 100,
) -> tuple[CompraSnapshot, ...]:
    return tuple(
        session.scalars(
            select(CompraSnapshot)
            .where(CompraSnapshot.empresa_id == empresa_id)
            .order_by(
                CompraSnapshot.guardado_en.desc(),
                CompraSnapshot.id.desc(),
            )
            .limit(limite)
        )
    )


def snapshot_como_dict(snapshot: CompraSnapshot) -> dict[str, object]:
    return {
        "id": snapshot.id,
        "empresa_id": snapshot.empresa_id,
        "spreadsheet_id": snapshot.spreadsheet_id,
        "modo_fuente": snapshot.modo_fuente,
        "contenido_hash": snapshot.contenido_hash,
        "cargado_en": snapshot.cargado_en.isoformat(),
        "guardado_en": (
            snapshot.guardado_en.isoformat()
            if snapshot.guardado_en is not None
            else None
        ),
        "lineas": snapshot.lineas,
        "esquema_valido": snapshot.esquema_valido,
        "rangos_por_pais": snapshot.rangos_por_pais,
        "diagnosticos": snapshot.diagnosticos,
    }
