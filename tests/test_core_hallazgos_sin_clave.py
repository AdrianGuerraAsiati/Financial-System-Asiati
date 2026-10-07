"""Hallazgos de wallets anteriores a la clave estable: cierre de datos legado (decisión 0008)."""
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import Auditoria
from app.core.hallazgos import Hallazgo, HallazgoMensaje
from app.core.hallazgos.sin_clave import hallazgos_sin_clave_con_trabajo
from app.core.usuarios import ROL_CONCILIACION
from tests.apoyo_auth import crear_empresa, crear_periodo, crear_usuario_prueba, engine

RAIZ = Path(__file__).resolve().parents[1]
NOTA = "Reemplazado por el hallazgo con clave estable."
BASE = "0020_tienda_reconciliations"


def _alembic() -> Config:
    config = Config(str(RAIZ / "alembic.ini"))
    config.set_main_option("script_location", str(RAIZ / "alembic"))
    config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    return config


def _hallazgo(periodo_id: int, *, motor: str = "conciliacion_wallets", clave: str | None = None,
              estado: str = "detectado", evidencia: dict | None = None) -> int:
    with Session(engine()) as session:
        h = Hallazgo(
            periodo_id=periodo_id,
            motor_slug=motor,
            codigo_regla="TIENDA_MOVIMIENTO_REVISAR",
            descripcion="Viejo",
            evidencia=evidencia or {"mov_id": 1},
            critico=False,
            resuelto=estado == "resuelto",
            estado=estado,
            clave=clave,
        )
        session.add(h)
        session.commit()
        return h.id


def _nota(hallazgo_id: int, usuario_id: int) -> None:
    with Session(engine()) as session:
        session.add(HallazgoMensaje(
            hallazgo_id=hallazgo_id,
            usuario_id=usuario_id,
            tipo="NOTA",
            texto="Revisado.",
        ))
        session.commit()


def _estado(hallazgo_id: int) -> tuple[str, bool, list[tuple[str, int | None, str]]]:
    with Session(engine()) as session:
        h = session.get(Hallazgo, hallazgo_id)
        mensajes = [
            (m.tipo, m.usuario_id, m.texto)
            for m in session.scalars(
                select(HallazgoMensaje)
                .where(HallazgoMensaje.hallazgo_id == hallazgo_id)
                .order_by(HallazgoMensaje.id)
            )
        ]
        return h.estado, h.resuelto, mensajes


def test_migracion_cierra_solo_los_viejos_sin_trabajo_de_personas_y_se_puede_revertir() -> None:
    empresa_id = crear_empresa("Sin clave")
    usuario_id, _ = crear_usuario_prueba(ROL_CONCILIACION, empresas=(empresa_id,))
    periodo_id = crear_periodo(empresa_id)
    command.downgrade(_alembic(), BASE)

    viejo = _hallazgo(periodo_id)
    con_nota = _hallazgo(periodo_id, estado="en_gestion")
    _nota(con_nota, usuario_id)
    categorizado = _hallazgo(
        periodo_id,
        evidencia={"mov_id": 2, "categorizacion": {"categoria": "RETIRO"}},
    )
    con_clave = _hallazgo(periodo_id, clave="TIENDA|t@x.co|TIENDA_MOVIMIENTO_REVISAR|3")
    otro_motor = _hallazgo(periodo_id, motor="cartera_ocs")

    command.upgrade(_alembic(), "head")

    assert _estado(viejo) == ("cerrado", True, [("SISTEMA", None, NOTA)])
    assert _estado(con_nota)[0] == "en_gestion"
    assert _estado(categorizado)[0] == "detectado"
    assert _estado(con_clave) == ("detectado", False, [])
    assert _estado(otro_motor) == ("detectado", False, [])
    with Session(engine()) as session:
        auditoria = session.scalar(
            select(Auditoria).where(
                Auditoria.accion == "hallazgo.cerrar_sin_clave",
                Auditoria.entidad_id == viejo,
            )
        )
        pendientes = {h.id for h in hallazgos_sin_clave_con_trabajo(session)}
    assert auditoria.antes == {"estado": "detectado", "resuelto": False}
    assert {con_nota, categorizado} <= pendientes and viejo not in pendientes

    command.downgrade(_alembic(), BASE)
    assert _estado(viejo) == ("detectado", False, [])
    assert _estado(con_nota)[0] == "en_gestion"
    assert _estado(categorizado)[0] == "detectado"

    command.upgrade(_alembic(), "head")
    assert _estado(viejo)[0] == "cerrado"
