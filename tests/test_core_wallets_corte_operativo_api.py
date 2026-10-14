"""Corte operativo: flujo HTTP real con PostgreSQL y usuarios sintéticos."""
from datetime import date, datetime, time, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
import pytest

from app.core.auditoria.model import Auditoria
from app.core.periodos import Periodo
from app.core.usuarios.roles import ROL_CONCILIACION, ROL_COORDINACION_FINANCIERA
from app.motores.conciliacion_wallets.corte_operativo import CorteOperativo
from tests.apoyo_auth import SECRETO_PRUEBA, cliente_con_rol, crear_empresa, crear_periodo, engine


@pytest.fixture(autouse=True)
def _auth(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRETO_PRUEBA)
    monkeypatch.setenv("AUTH_PROVIDER", "local")


def _ctx():
    empresa = crear_empresa("Corte API")
    periodo = crear_periodo(empresa)
    with Session(engine()) as session:
        p = session.get(Periodo, periodo)
        corte_local = datetime.combine(p.fecha_fin, time(23, 59, 59))
    return empresa, periodo, f"/api/v1/wallets/periodos/{periodo}/corte-operativo", corte_local


def test_corte_autorizado_persistido_auditado_y_sin_sobrescritura():
    empresa, periodo, ruta, corte_local = _ctx()
    conciliador, _ = cliente_con_rol(ROL_CONCILIACION, empresas=(empresa,))
    coordinacion, coord_id = cliente_con_rol(ROL_COORDINACION_FINANCIERA, empresas=(empresa,))
    params = {"empresa_id": empresa}
    body = {"zona_horaria": "America/Bogota", "corte_local": corte_local.isoformat(),
            "motivo": "Prueba de corte definida por usuario"}
    assert conciliador.get(ruta, params=params).json()["configurado"] is False
    assert conciliador.post(ruta, params=params, json=body).status_code == 403
    created = coordinacion.post(ruta, params=params, json=body)
    assert created.status_code == 201, created.text
    assert coordinacion.post(ruta, params=params, json=body).status_code == 422
    read = conciliador.get(ruta, params=params)
    assert read.status_code == 200, read.text
    assert read.json()["zona_horaria"] == "America/Bogota"
    with Session(engine()) as session:
        corte = session.scalar(select(CorteOperativo).where(CorteOperativo.periodo_id == periodo))
        assert corte.registrado_por == coord_id
        assert corte.corte_utc == corte_local.replace(tzinfo=timezone.utc) + timedelta(hours=5)
        auditoria = session.scalar(select(Auditoria).where(
            Auditoria.entidad == "wallets_cortes_operativos", Auditoria.entidad_id == corte.id))
        assert auditoria is not None
        assert auditoria.usuario_id == coord_id


def test_rechaza_zona_distinta_y_empresa_no_asignada():
    empresa, _, ruta, corte_local = _ctx()
    otra = crear_empresa("Ajena corte API")
    coordinacion, _ = cliente_con_rol(ROL_COORDINACION_FINANCIERA, empresas=(empresa,))
    body = {"zona_horaria": "UTC", "corte_local": corte_local.isoformat(),
            "motivo": "Debe ser rechazado"}
    assert coordinacion.post(ruta, params={"empresa_id": empresa}, json=body).status_code == 422
    assert coordinacion.get(ruta, params={"empresa_id": otra}).status_code == 404
    assert coordinacion.post(ruta, params={"empresa_id": otra}, json=body).status_code == 404


def test_corte_de_periodo_cerrado_es_rechazado():
    empresa, periodo, ruta, corte_local = _ctx()
    with Session(engine()) as session:
        session.get(Periodo, periodo).cerrado = True
        session.commit()
    coordinacion, _ = cliente_con_rol(ROL_COORDINACION_FINANCIERA, empresas=(empresa,))
    response = coordinacion.post(ruta, params={"empresa_id": empresa}, json={
        "zona_horaria": "America/Bogota", "corte_local": corte_local.isoformat(),
        "motivo": "Debe bloquearse",
    })
    assert response.status_code == 422
