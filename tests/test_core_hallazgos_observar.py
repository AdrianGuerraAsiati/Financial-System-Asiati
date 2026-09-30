"""Observación del conciliador sobre un hallazgo (hallazgos.gestionar)."""
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import Auditoria
from app.core.hallazgos import Hallazgo, HallazgoMensaje
from app.core.usuarios import ROL_CONCILIACION, ROL_COORDINACION_FINANCIERA, ROL_TI
from tests.apoyo_auth import (
    SECRETO_PRUEBA,
    cliente_con_rol,
    crear_empresa,
    crear_hallazgo,
    crear_periodo,
    engine,
)


@pytest.fixture(autouse=True)
def entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", SECRETO_PRUEBA)


def _observar(client, hallazgo_id: int, observacion: str | None, resolver: bool = False):
    return client.post(
        f"/api/v1/hallazgos/{hallazgo_id}/observar",
        json={"observacion": observacion, "resolver": resolver},
    )


def _mensajes(hallazgo_id: int) -> list[HallazgoMensaje]:
    with Session(engine()) as session:
        return list(
            session.scalars(
                select(HallazgoMensaje).where(HallazgoMensaje.hallazgo_id == hallazgo_id)
            )
        )


def _auditoria(hallazgo_id: int) -> list[Auditoria]:
    with Session(engine()) as session:
        return list(
            session.scalars(
                select(Auditoria).where(
                    Auditoria.accion == "hallazgo.observar",
                    Auditoria.entidad_id == hallazgo_id,
                )
            )
        )


def test_observation_leaves_note_state_and_audit_row() -> None:
    empresa_id = crear_empresa()
    hallazgo_id = crear_hallazgo(crear_periodo(empresa_id))
    client, usuario_id = cliente_con_rol(ROL_CONCILIACION, empresas=(empresa_id,))

    respuesta = _observar(client, hallazgo_id, "  Transferencia a proveedor de empaques  ")
    detalle = client.get(f"/api/v1/hallazgos/{hallazgo_id}").json()

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "en_gestion"
    assert respuesta.json()["resuelto"] is False
    assert [(m["tipo"], m["usuario_id"], m["texto"]) for m in detalle["mensajes"]] == [
        ("NOTA", usuario_id, "Transferencia a proveedor de empaques"),
    ]
    [fila] = _auditoria(hallazgo_id)
    assert fila.usuario_id == usuario_id
    assert fila.empresa_id == empresa_id
    assert fila.antes == {"estado": "detectado", "resuelto": False}
    assert fila.despues == {
        "estado": "en_gestion",
        "resuelto": False,
        "observacion": "Transferencia a proveedor de empaques",
    }


def test_observation_can_mark_finding_resolved() -> None:
    empresa_id = crear_empresa()
    hallazgo_id = crear_hallazgo(crear_periodo(empresa_id))
    client, _ = cliente_con_rol(ROL_COORDINACION_FINANCIERA, empresas=(empresa_id,))

    respuesta = _observar(client, hallazgo_id, "Pago de tiquetes aprobado", resolver=True)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "resuelto"
    with Session(engine()) as session:
        assert session.get(Hallazgo, hallazgo_id).resuelto is True


def test_observation_without_text_is_rejected_and_changes_nothing() -> None:
    empresa_id = crear_empresa()
    hallazgo_id = crear_hallazgo(crear_periodo(empresa_id))
    client, _ = cliente_con_rol(ROL_CONCILIACION, empresas=(empresa_id,))

    respuesta = _observar(client, hallazgo_id, "   ", resolver=True)

    assert respuesta.status_code == 422
    assert "observación" in respuesta.json()["detail"]
    with Session(engine()) as session:
        hallazgo = session.get(Hallazgo, hallazgo_id)
        assert (hallazgo.estado, hallazgo.resuelto) == ("detectado", False)
    assert _mensajes(hallazgo_id) == []
    assert _auditoria(hallazgo_id) == []


def test_escalated_finding_waits_for_the_coordinator() -> None:
    empresa_id = crear_empresa()
    hallazgo_id = crear_hallazgo(crear_periodo(empresa_id), estado="escalado")
    client, _ = cliente_con_rol(ROL_CONCILIACION, empresas=(empresa_id,))

    respuesta = _observar(client, hallazgo_id, "Ya lo revisé", resolver=True)

    assert respuesta.status_code == 409
    assert "coordinador" in respuesta.json()["detail"]
    assert _mensajes(hallazgo_id) == []


def test_findings_of_a_closed_period_cannot_be_observed() -> None:
    empresa_id = crear_empresa()
    hallazgo_id = crear_hallazgo(crear_periodo(empresa_id, cerrado=True))
    client, _ = cliente_con_rol(ROL_CONCILIACION, empresas=(empresa_id,))

    respuesta = _observar(client, hallazgo_id, "Observación")

    assert respuesta.status_code == 409
    assert "cerrado" in respuesta.json()["detail"]
    assert _mensajes(hallazgo_id) == []


def test_unassigned_company_is_not_found() -> None:
    propia = crear_empresa()
    ajena = crear_empresa()
    hallazgo_id = crear_hallazgo(crear_periodo(ajena))
    client, _ = cliente_con_rol(ROL_CONCILIACION, empresas=(propia,))

    respuesta = _observar(client, hallazgo_id, "Observación")

    assert respuesta.status_code == 404
    assert _mensajes(hallazgo_id) == []


def test_it_support_cannot_observe() -> None:
    empresa_id = crear_empresa()
    hallazgo_id = crear_hallazgo(crear_periodo(empresa_id))
    client, _ = cliente_con_rol(ROL_TI, empresas=(empresa_id,))

    respuesta = _observar(client, hallazgo_id, "Observación")

    assert respuesta.status_code == 403
    assert _mensajes(hallazgo_id) == []
