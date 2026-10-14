"""Revisión completa HTTP y PostgreSQL con datos sintéticos y roles separados."""
from datetime import datetime, time, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria.model import Auditoria
from app.core.periodos import Periodo
from app.core.usuarios.roles import ROL_CONCILIACION, ROL_COORDINACION_FINANCIERA
from app.motores.conciliacion_wallets.revision_tardios import RevisionTardio
from tests.apoyo_auth import SECRETO_PRUEBA, cliente_con_rol, crear_empresa, crear_periodo, engine


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRETO_PRUEBA)
    monkeypatch.setenv("AUTH_PROVIDER", "local")


def test_revision_y_decision_sin_alterar_periodo():
    empresa = crear_empresa("Revisión tardíos")
    periodo = crear_periodo(empresa)
    conciliacion, revisor_id = cliente_con_rol(ROL_CONCILIACION, empresas=(empresa,))
    finanzas, aprobador_id = cliente_con_rol(ROL_COORDINACION_FINANCIERA, empresas=(empresa,))
    with Session(engine()) as session:
        fecha_fin = session.get(Periodo, periodo).fecha_fin
    local = datetime.combine(fecha_fin, time(23, 59, 59))
    ruta = f"/api/v1/wallets/periodos/{periodo}"
    params = {"empresa_id": empresa}
    corte = finanzas.post(f"{ruta}/corte-operativo", params=params,
        json={"zona_horaria": "America/Bogota", "corte_local": local.isoformat(),
              "motivo": "Prueba sintética"})
    assert corte.status_code == 201, corte.text
    corte_utc = local.replace(tzinfo=timezone.utc) + timedelta(hours=5)
    movimiento = conciliacion.post(f"{ruta}/movimientos-tardios", params=params,
        json={"tipo_wallet": "wiilog", "identificador_externo": "prueba-review-1",
              "instante_movimiento": (corte_utc - timedelta(seconds=10)).isoformat(),
              "instante_recepcion": (corte_utc + timedelta(seconds=10)).isoformat(),
              "evidencia_ref": "prueba://movimiento/1"})
    assert movimiento.status_code == 201, movimiento.text
    item_id = movimiento.json()["id"]
    ruta_item = f"{ruta}/movimientos-tardios/{item_id}"
    assert finanzas.post(f"{ruta_item}/decidir", params=params,
        json={"decision": "AUTORIZAR_GESTION", "justificacion": "sin revisar"}).status_code == 422
    assert finanzas.post(f"{ruta_item}/revisar", params=params,
        json={"conclusion": "REQUIERE_CORRECCION", "justificacion": "x",
              "evidencia_revision": "prueba://1"}).status_code == 403
    revision = conciliacion.post(f"{ruta_item}/revisar", params=params,
        json={"conclusion": "REQUIERE_CORRECCION", "justificacion": "Afecta corte",
              "evidencia_revision": "prueba://revision/1"})
    assert revision.status_code == 201, revision.text
    assert conciliacion.post(f"{ruta_item}/revisar", params=params,
        json={"conclusion": "SIN_IMPACTO", "justificacion": "Repetición",
              "evidencia_revision": "prueba://revision/2"}).status_code == 422
    assert conciliacion.post(f"{ruta_item}/decidir", params=params,
        json={"decision": "AUTORIZAR_GESTION", "justificacion": "No permitido"}).status_code == 403
    decision = finanzas.post(f"{ruta_item}/decidir", params=params,
        json={"decision": "AUTORIZAR_GESTION", "justificacion": "Gestionar por flujo separado"})
    assert decision.status_code == 200, decision.text
    assert decision.json()["decision"] == "AUTORIZAR_GESTION"
    assert finanzas.post(f"{ruta_item}/decidir", params=params,
        json={"decision": "RECHAZAR_GESTION", "justificacion": "No duplicar"}).status_code == 422
    lista = conciliacion.get(f"{ruta}/revisiones-tardios", params=params)
    assert lista.status_code == 200, lista.text
    assert lista.json()[0]["revisado_por"] == revisor_id
    assert lista.json()[0]["autorizado_por"] == aprobador_id
    with Session(engine()) as session:
        assert session.get(Periodo, periodo).cerrado is False
        row = session.scalar(select(RevisionTardio).where(RevisionTardio.movimiento_id == item_id))
        assert row.decision == "AUTORIZAR_GESTION"
        eventos = list(session.scalars(select(Auditoria).where(
            Auditoria.entidad == "wallets_tardios_revisiones",
            Auditoria.entidad_id == row.id,
        )))
        assert {e.accion for e in eventos} == {"WALLET_TARDIO_REVISAR", "WALLET_TARDIO_DECIDIR"}
