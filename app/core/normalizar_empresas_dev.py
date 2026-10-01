"""Normaliza empresas heredadas del entorno de desarrollo.

Este módulo solo puede ejecutarse con APP_ENV=development. Migra las referencias
técnicas de ASIATI Demo a ASIATI y elimina la empresa demo si no contiene
períodos, fuentes ni cargas operativas.
"""
from __future__ import annotations

import json
import os

from sqlalchemy import delete, func, select, update

from app.core.auditoria.model import Auditoria
from app.core.cargas import Carga
from app.core.empresas import Empresa
from app.core.fuentes import Fuente
from app.core.periodos import Periodo
from app.core.session import crear_session
from app.core.usuarios import UsuarioEmpresa
from app.motores.compras_supply_chain.model import (
    CompraSnapshot,
    CompraSnapshotLinea,
)


EMPRESA_REAL = "ASIATI"
EMPRESA_DEMO = "ASIATI Demo"


def _conteo(session, modelo, empresa_id: int) -> int:
    return int(
        session.scalar(
            select(func.count()).select_from(modelo).where(
                modelo.empresa_id == empresa_id
            )
        )
        or 0
    )


def normalizar() -> dict[str, object]:
    if os.getenv("APP_ENV", "development").strip().lower() != "development":
        raise RuntimeError(
            "La normalización de empresas demo solo puede ejecutarse en development."
        )

    with crear_session() as session:
        real = session.scalar(
            select(Empresa).where(Empresa.nombre == EMPRESA_REAL).order_by(Empresa.id)
        )
        if real is None:
            raise RuntimeError(
                "Falta la empresa ASIATI. Aplica primero los datos base de Wallets."
            )

        demo = session.scalar(
            select(Empresa).where(Empresa.nombre == EMPRESA_DEMO).order_by(Empresa.id)
        )
        if demo is None:
            return {
                "empresa_asiati_id": real.id,
                "demo_eliminada": False,
                "motivo": "ASIATI Demo ya no existe.",
            }

        bloqueos = {
            "periodos": _conteo(session, Periodo, demo.id),
            "fuentes": _conteo(session, Fuente, demo.id),
            "cargas": _conteo(session, Carga, demo.id),
        }
        if any(bloqueos.values()):
            raise RuntimeError(
                "ASIATI Demo contiene datos operativos y no se elimina automáticamente: "
                + json.dumps(bloqueos, ensure_ascii=False)
            )

        asignaciones = list(
            session.scalars(
                select(UsuarioEmpresa).where(UsuarioEmpresa.empresa_id == demo.id)
            )
        )
        for asignacion in asignaciones:
            destino = session.get(
                UsuarioEmpresa,
                (asignacion.usuario_id, real.id),
            )
            if destino is None:
                asignacion.empresa_id = real.id
            else:
                session.delete(asignacion)

        snapshots = list(
            session.scalars(
                select(CompraSnapshot).where(CompraSnapshot.empresa_id == demo.id)
            )
        )
        for snapshot in snapshots:
            existente = session.scalar(
                select(CompraSnapshot).where(
                    CompraSnapshot.empresa_id == real.id,
                    CompraSnapshot.contenido_hash == snapshot.contenido_hash,
                )
            )
            if existente is None:
                snapshot.empresa_id = real.id
                continue

            session.execute(
                delete(CompraSnapshotLinea).where(
                    CompraSnapshotLinea.snapshot_id == snapshot.id
                )
            )
            session.delete(snapshot)

        session.execute(
            update(Auditoria)
            .where(Auditoria.empresa_id == demo.id)
            .values(empresa_id=real.id)
        )

        session.delete(demo)
        session.commit()

        empresas = list(session.scalars(select(Empresa).order_by(Empresa.id)))
        return {
            "empresa_asiati_id": real.id,
            "demo_eliminada": True,
            "empresas": [empresa.nombre for empresa in empresas],
        }


def main() -> int:
    print(json.dumps(normalizar(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
