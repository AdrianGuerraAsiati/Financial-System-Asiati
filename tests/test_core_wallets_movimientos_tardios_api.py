"""Incidencias temporales: integración HTTP + PostgreSQL, sin cambios de saldos."""
from datetime import datetime, time, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria.model import Auditoria
from app.core.periodos import Periodo
from app.core.usuarios.roles import ROL_CONCILIACION, ROL_COORDINACION_FINANCIERA
from app.motores.conciliacion_wallets.corte_operativo import CorteOperativo
from app.motores.conciliacion_wallets.movimientos_tardios import MovimientoTardio
from tests.apoyo_auth import SECRETO_PRUEBA, cliente_con_rol, crear_empresa, crear_periodo, engine


@pytest.fixture(autouse=True)
def auth(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRETO_PRUEBA)
    monkeypatch.setenv("AUTH_PROVIDER", "local")


def contexto(*, cerrado=False):
    empresa = crear_empresa("Incidencias temporales")
    periodo = crear_periodo(empresa)
    coordinacion, coordinacion_id = cliente_con_rol(ROL_COORDINACION_FINANCIERA, empresas=(empresa,))
    conciliador, conciliador_id = cliente_con_rol(ROL_CONCILIACION, empresas=(empresa,))
    with Session(engine()) as session:
        p = session.get(Periodo, periodo)
        local = datetime.combine(p.fecha_fin, time(23, 59, 59))
    params = {"empresa_id": empresa}
    registro_corte = coordinacion.post(
        f"/api/v1/wallets/periodos/{periodo}/corte-operativo", params=params,
        json={"zona_horaria": "America/Bogota", "corte_local": local.isoformat(),
              "motivo": "Corte sintético de integración"},
    )
    assert registro_corte.status_code == 201, registro_corte.text
    if cerrado:
        with Session(engine()) as session:
            session.get(Periodo, periodo).cerrado = True
            session.commit()
    corte_utc = local.replace(tzinfo=timezone.utc) + timedelta(hours=5)
    return empresa, periodo, conciliador, coordinacion, conciliador_id, corte_utc


def payload(corte, *, ident="MOV-SINTETICO-1", tardio=True):
    antes = corte - timedelta(seconds=20)
    despues = corte + timedelta(seconds=20)
    return {
        "tipo_wallet": "wiilog", "identidad_wallet": None,
        "identificador_externo": ident,
        "instante_movimiento": (antes if tardio else despues).isoformat(),
        "instante_recepcion": despues.isoformat(),
        "evidencia_ref": "prueba://carga-sintetica/1",
    }


def test_registro_tardio_auditado_y_unico():
    empresa, periodo, conciliador, coordinacion, usuario, corte = contexto()
    ruta = f"/api/v1/wallets/periodos/{periodo}/movimientos-tardios"
    params = {"empresa_id": empresa}
    result = conciliador.post(ruta, params=params, json=payload(corte))
    assert result.status_code == 201, result.text
    assert result.json()["clasificacion"] == "TARDIO_DEL_PERIODO"
    assert conciliador.post(ruta, params=params, json=payload(corte)).status_code == 422
    consulta = coordinacion.get(ruta, params=params)
    assert consulta.status_code == 200, consulta.text
    assert [x["clasificacion"] for x in consulta.json()] == ["TARDIO_DEL_PERIODO"]
    with Session(engine()) as session:
        fila = session.scalar(select(MovimientoTardio).where(MovimientoTardio.periodo_id == periodo))
        assert fila.registrado_por == usuario
        assert fila.evidencia_ref == "prueba://carga-sintetica/1"
        auditoria = session.scalar(select(Auditoria).where(
            Auditoria.entidad == "wallets_movimientos_tardios",
            Auditoria.entidad_id == fila.id))
        assert auditoria is not None
        assert auditoria.usuario_id == usuario


def test_solo_registra_fuera_de_corte_y_con_corte_previo():
    empresa, periodo, conciliador, _, _, corte = contexto()
    ruta = f"/api/v1/wallets/periodos/{periodo}/movimientos-tardios"
    datos = payload(corte)
    datos["instante_recepcion"] = (corte - timedelta(seconds=1)).isoformat()
    assert conciliador.post(ruta, params={"empresa_id": empresa}, json=datos).status_code == 422
    posterior = conciliador.post(ruta, params={"empresa_id": empresa},
                                 json=payload(corte, ident="MOV-SINTETICO-2", tardio=False))
    assert posterior.status_code == 201, posterior.text
    assert posterior.json()["clasificacion"] == "POST_CORTE"


def test_permisos_empresa_y_reporte_sin_mutacion_cerrada():
    empresa, periodo, conciliador, coordinacion, _, corte = contexto(cerrado=True)
    ruta = f"/api/v1/wallets/periodos/{periodo}/movimientos-tardios"
    datos = payload(corte)
    ajena = crear_empresa("Incidencia ajena")
    assert conciliador.post(ruta, params={"empresa_id": ajena}, json=datos).status_code == 404
    assert coordinacion.post(ruta, params={"empresa_id": empresa}, json=datos).status_code == 403
    assert conciliador.post(ruta, params={"empresa_id": empresa}, json=datos).status_code == 201
    with Session(engine()) as session:
        assert session.get(Periodo, periodo).cerrado is True
        assert session.scalar(select(CorteOperativo).where(CorteOperativo.periodo_id == periodo)) is not None
