"""Clave estable de hallazgos de motor: reconciliar no pierde el trabajo del conciliador (decisión 0008)."""
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auditoria import Auditoria
from app.core.hallazgos import (
    Hallazgo,
    HallazgoMensaje,
    HallazgoMotorNuevo,
    sincronizar_hallazgos_motor,
)
from app.core.usuarios import ROL_CONCILIACION
from tests.apoyo_auth import crear_empresa, crear_periodo, crear_usuario_prueba, engine

MOTOR = "conciliacion_wallets"
ALCANCE = "TIENDA|tienda@x.co|"


def _nuevo(mov_id: int, monto: str = "1000.00") -> HallazgoMotorNuevo:
    return HallazgoMotorNuevo(
        clave=f"{ALCANCE}TIENDA_MOVIMIENTO_REVISAR|{mov_id}",
        codigo_regla="TIENDA_MOVIMIENTO_REVISAR",
        descripcion="El movimiento requiere revisión.",
        evidencia={"mov_id": mov_id, "monto": monto},
        critico=False,
    )


def _contexto() -> tuple[int, int]:
    empresa_id = crear_empresa("Sincronizar")
    usuario_id, _ = crear_usuario_prueba(ROL_CONCILIACION, empresas=(empresa_id,))
    return crear_periodo(empresa_id), usuario_id


def _sincronizar(periodo_id: int, usuario_id: int, nuevos: list[HallazgoMotorNuevo], alcance: str = ALCANCE):
    with Session(engine()) as session:
        resultado = sincronizar_hallazgos_motor(
            session,
            periodo_id=periodo_id,
            motor_slug=MOTOR,
            alcance_clave=alcance,
            hallazgos=nuevos,
            usuario_id=usuario_id,
        )
        session.commit()
        return resultado


def _hallazgo(periodo_id: int, mov_id: int) -> Hallazgo:
    with Session(engine()) as session:
        return session.scalar(
            select(Hallazgo).where(
                Hallazgo.periodo_id == periodo_id,
                Hallazgo.clave == f"{ALCANCE}TIENDA_MOVIMIENTO_REVISAR|{mov_id}",
            )
        )


def _mensajes(hallazgo_id: int) -> list[tuple[str, str]]:
    with Session(engine()) as session:
        return [
            (m.tipo, m.texto)
            for m in session.scalars(
                select(HallazgoMensaje).where(HallazgoMensaje.hallazgo_id == hallazgo_id).order_by(HallazgoMensaje.id)
            )
        ]


def _gestionar(hallazgo_id: int, usuario_id: int, *, estado: str, categorizacion: dict | None = None) -> None:
    with Session(engine()) as session:
        h = session.get(Hallazgo, hallazgo_id)
        h.estado = estado
        h.resuelto = estado == "resuelto"
        if categorizacion is not None:
            h.evidencia = {**h.evidencia, "categorizacion": categorizacion}
        session.add(HallazgoMensaje(hallazgo_id=h.id, usuario_id=usuario_id, tipo="NOTA", texto="Revisado."))
        session.commit()


def test_reconciliar_actualiza_la_evidencia_y_conserva_estado_mensajes_y_categorizacion() -> None:
    periodo_id, usuario_id = _contexto()
    primera = _sincronizar(periodo_id, usuario_id, [_nuevo(1)])
    assert primera.creados == 1
    h = _hallazgo(periodo_id, 1)
    _gestionar(h.id, usuario_id, estado="en_gestion", categorizacion={"categoria": "FLETE"})

    segunda = _sincronizar(periodo_id, usuario_id, [_nuevo(1, monto="1500.00")])

    assert (segunda.creados, segunda.actualizados) == (0, 1)
    despues = _hallazgo(periodo_id, 1)
    assert despues.id == h.id
    assert despues.estado == "en_gestion"
    assert despues.evidencia["monto"] == "1500.00"
    assert despues.evidencia["categorizacion"] == {"categoria": "FLETE"}
    assert _mensajes(h.id) == [("NOTA", "Revisado.")]


def test_lo_que_ya_no_aparece_queda_resuelto_por_el_sistema_con_nota_y_auditoria() -> None:
    periodo_id, usuario_id = _contexto()
    _sincronizar(periodo_id, usuario_id, [_nuevo(1), _nuevo(2)])

    resultado = _sincronizar(periodo_id, usuario_id, [_nuevo(1)])

    assert resultado.resueltos_por_sistema == 1
    h = _hallazgo(periodo_id, 2)
    assert (h.estado, h.resuelto, h.resuelto_por_sistema) == ("resuelto", True, True)
    [(tipo, texto)] = _mensajes(h.id)
    assert tipo == "SISTEMA" and "ya no aparece" in texto.lower()
    with Session(engine()) as session:
        acciones = session.scalars(
            select(Auditoria.accion).where(Auditoria.entidad == "hallazgo", Auditoria.entidad_id == h.id)
        ).all()
    assert "hallazgo.resolver_sistema" in acciones


def test_resuelto_por_el_sistema_que_reaparece_se_reabre_como_detectado() -> None:
    periodo_id, usuario_id = _contexto()
    _sincronizar(periodo_id, usuario_id, [_nuevo(1), _nuevo(2)])
    _sincronizar(periodo_id, usuario_id, [_nuevo(1)])

    resultado = _sincronizar(periodo_id, usuario_id, [_nuevo(1), _nuevo(2)])

    assert resultado.reabiertos == 1
    h = _hallazgo(periodo_id, 2)
    assert (h.estado, h.resuelto, h.resuelto_por_sistema) == ("detectado", False, False)
    assert [t for t, _ in _mensajes(h.id)] == ["SISTEMA", "SISTEMA"]
    assert "reaparec" in _mensajes(h.id)[-1][1].lower()


def test_resuelto_por_una_persona_que_sigue_apareciendo_se_queda_resuelto() -> None:
    periodo_id, usuario_id = _contexto()
    _sincronizar(periodo_id, usuario_id, [_nuevo(1)])
    h = _hallazgo(periodo_id, 1)
    _gestionar(h.id, usuario_id, estado="resuelto", categorizacion={"categoria": "RETIRO"})

    resultado = _sincronizar(periodo_id, usuario_id, [_nuevo(1, monto="2000.00")])

    assert resultado.reabiertos == 0
    despues = _hallazgo(periodo_id, 1)
    assert (despues.estado, despues.resuelto, despues.resuelto_por_sistema) == ("resuelto", True, False)
    assert despues.evidencia["monto"] == "2000.00"
    assert despues.evidencia["categorizacion"] == {"categoria": "RETIRO"}
    assert _mensajes(h.id) == [("NOTA", "Revisado.")]


def test_otra_wallet_fuera_del_alcance_no_se_toca() -> None:
    periodo_id, usuario_id = _contexto()
    otra = HallazgoMotorNuevo(
        clave="TIENDA|otra@x.co|TIENDA_MOVIMIENTO_REVISAR|9",
        codigo_regla="TIENDA_MOVIMIENTO_REVISAR",
        descripcion="Otra wallet.",
        evidencia={"mov_id": 9},
        critico=False,
    )
    _sincronizar(periodo_id, usuario_id, [otra], alcance="TIENDA|otra@x.co|")

    _sincronizar(periodo_id, usuario_id, [_nuevo(1)])

    with Session(engine()) as session:
        h = session.scalar(select(Hallazgo).where(Hallazgo.clave == otra.clave, Hallazgo.periodo_id == periodo_id))
    assert h.estado == "detectado"


def test_la_clave_no_se_repite_en_el_mismo_periodo_y_motor() -> None:
    periodo_id, _ = _contexto()
    with Session(engine()) as session:
        for _ in range(2):
            session.add(
                Hallazgo(periodo_id=periodo_id, motor_slug=MOTOR, codigo_regla="X", descripcion="x",
                         evidencia={}, critico=False, clave="TIENDA|t@x.co|X|1")
            )
        with pytest.raises(IntegrityError):
            session.flush()
