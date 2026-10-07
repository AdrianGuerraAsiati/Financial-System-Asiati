"""Hallazgos de wallets anteriores a la clave estable que tienen trabajo de una persona (decisión 0008).

La migración 0021 cierra los demás. Estos quedan abiertos para que negocio decida:

    python -m app.core.hallazgos.sin_clave
"""
from __future__ import annotations

import json

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.core.hallazgos.mensajes import TIPO_SISTEMA, HallazgoMensaje
from app.core.hallazgos.model import Hallazgo
from app.core.periodos import Periodo

MOTOR_WALLETS = "conciliacion_wallets"


def hallazgos_sin_clave_con_trabajo(session: Session) -> list[Hallazgo]:
    con_mensajes = exists().where(
        HallazgoMensaje.hallazgo_id == Hallazgo.id,
        HallazgoMensaje.tipo != TIPO_SISTEMA,
    )
    categorizado = Hallazgo.evidencia.has_key("categorizacion")
    return list(
        session.scalars(
            select(Hallazgo)
            .where(
                Hallazgo.motor_slug == MOTOR_WALLETS,
                Hallazgo.clave.is_(None),
                Hallazgo.estado != "cerrado",
                con_mensajes | categorizado,
            )
            .order_by(Hallazgo.id)
        )
    )


def main() -> int:
    from app.core.session import crear_session

    with crear_session() as session:
        filas = []
        for h in hallazgos_sin_clave_con_trabajo(session):
            periodo = session.get(Periodo, h.periodo_id)
            tipos = session.scalars(
                select(HallazgoMensaje.tipo)
                .where(HallazgoMensaje.hallazgo_id == h.id)
                .order_by(HallazgoMensaje.id)
            ).all()
            filas.append({
                "id": h.id,
                "empresa_id": periodo.empresa_id,
                "periodo_id": h.periodo_id,
                "codigo_regla": h.codigo_regla,
                "estado": h.estado,
                "mensajes": list(tipos),
                "categorizado": "categorizacion" in (h.evidencia or {}),
            })
    print(json.dumps({"pendientes_de_decision": filas}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
