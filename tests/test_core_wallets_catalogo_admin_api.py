"""Flujo real de catálogo con PostgreSQL, endpoints y roles. Solo datos sintéticos."""
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria.model import Auditoria
from app.core.periodos import Periodo
from app.core.usuarios.roles import (
    ROL_CONCILIACION, ROL_COORDINACION_FINANCIERA, ROL_TI,
)
from app.motores.conciliacion_wallets import catalogo_admin
from app.motores.conciliacion_wallets.catalogo_admin import WalletCatalogoAprobacion
from app.motores.conciliacion_wallets.esperadas import WalletEsperada
from tests.apoyo_auth import (
    SECRETO_PRUEBA, cliente_con_rol, crear_empresa, crear_periodo, engine,
)


@pytest.fixture(autouse=True)
def auth(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRETO_PRUEBA)
    monkeypatch.setenv("AUTH_PROVIDER", "local")


def contexto(monkeypatch):
    empresa_id = crear_empresa("Catalogo wallet")
    periodo_id = crear_periodo(empresa_id)
    otra_empresa_id = crear_empresa("Otra empresa catalogo")
    configuracion = {
        "wiilog": True,
        "tiendas": [{"usuario_email": "tienda@sintetico.test"}],
        "pagos": [{"usuario_email": "pagos@sintetico.test"}],
    }
    monkeypatch.setattr(catalogo_admin, "catalogo_de_empresa", lambda session, eid: configuracion if eid == empresa_id else {"wiilog": False, "tiendas": [], "pagos": []})
    ruta = f"/api/v1/wallets/periodos/{periodo_id}/wallets-esperadas"
    with Session(engine()) as session:
        periodo = session.get(Periodo, periodo_id)
        rango = (periodo.fecha_inicio.isoformat(), periodo.fecha_fin.isoformat())
    return empresa_id, otra_empresa_id, periodo_id, ruta, rango


def test_flujo_alta_baja_aprobacion_y_congelacion(monkeypatch):
    empresa, _, periodo, ruta, (inicio, fin) = contexto(monkeypatch)
    conciliador, conciliador_id = cliente_con_rol(ROL_CONCILIACION, empresas=(empresa,))
    coordinacion, coordinacion_id = cliente_con_rol(ROL_COORDINACION_FINANCIERA, empresas=(empresa,))
    params = {"empresa_id": empresa}
    wallet = {"tipo_wallet": "pagos", "identidad_wallet": " PAGOS@SINTETICO.TEST ",
              "vigente_desde": inicio, "vigente_hasta": fin}

    creada = conciliador.post(ruta, params=params, json=wallet)
    assert creada.status_code == 201, creada.text
    id_baja = creada.json()["id"]
    assert creada.json()["identidad_wallet"] == "pagos@sintetico.test"

    eliminado = conciliador.request(
        "DELETE", f"{ruta}/{id_baja}", params=params, json={"motivo": "Corrección sintética"}
    )
    assert eliminado.status_code == 204, eliminado.text
    segunda = conciliador.post(ruta, params=params, json=wallet)
    assert segunda.status_code == 201, segunda.text
    id_aprobado = segunda.json()["id"]

    listado = conciliador.get(ruta, params=params)
    assert listado.status_code == 200, listado.text
    assert listado.json()["aprobado"] is False
    assert [w["id"] for w in listado.json()["wallets"]] == [id_aprobado]

    assert conciliador.post(f"{ruta}/aprobar", params=params, json={"motivo": "Revisión"}).status_code == 403
    aprobada = coordinacion.post(
        f"{ruta}/aprobar", params=params, json={"motivo": "Cobertura sintética revisada"}
    )
    assert aprobada.status_code == 201, aprobada.text
    assert coordinacion.get(ruta, params=params).json()["aprobado"] is True

    assert conciliador.post(ruta, params=params, json={"tipo_wallet": "wiilog",
           "vigente_desde": inicio, "vigente_hasta": fin}).status_code == 409
    assert conciliador.request("DELETE", f"{ruta}/{id_aprobado}",
           params=params, json={"motivo": "No debe poderse"}).status_code == 409
    assert coordinacion.post(f"{ruta}/aprobar", params=params,
           json={"motivo": "Doble aprobación"}).status_code == 409

    with Session(engine()) as session:
        filas = list(session.scalars(select(WalletEsperada).where(WalletEsperada.periodo_id == periodo)))
        assert len(filas) == 1
        aprobado = session.scalar(select(WalletCatalogoAprobacion).where(
            WalletCatalogoAprobacion.periodo_id == periodo))
        assert aprobado.aprobado_por == coordinacion_id
        assert aprobado.wallets_snapshot[0]["id"] == id_aprobado
        eventos = list(session.scalars(select(Auditoria).where(
            Auditoria.empresa_id == empresa,
            Auditoria.entidad.in_(("wallets_esperadas", "wallets_catalogo_aprobaciones")),
        )))
        assert {e.accion for e in eventos} >= {
            "WALLET_CATALOGO_AGREGAR", "WALLET_CATALOGO_QUITAR", "WALLET_CATALOGO_APROBAR"
        }
        assert any(e.usuario_id == conciliador_id for e in eventos)


def test_permisos_y_aislamiento_por_empresa(monkeypatch):
    empresa, otra, _, ruta, (inicio, fin) = contexto(monkeypatch)
    conciliador, _ = cliente_con_rol(ROL_CONCILIACION, empresas=(empresa,))
    coordinacion, _ = cliente_con_rol(ROL_COORDINACION_FINANCIERA, empresas=(empresa,))
    ti, _ = cliente_con_rol(ROL_TI)
    body = {"tipo_wallet": "wiilog", "vigente_desde": inicio, "vigente_hasta": fin}
    assert conciliador.get(ruta, params={"empresa_id": otra}).status_code == 404
    assert conciliador.post(ruta, params={"empresa_id": otra}, json=body).status_code == 404
    assert coordinacion.post(ruta, params={"empresa_id": empresa}, json=body).status_code == 403
    assert ti.get(ruta, params={"empresa_id": empresa}).status_code == 200
    assert ti.post(ruta, params={"empresa_id": empresa}, json=body).status_code == 403


def test_sin_vigencia_no_aprueba_y_periodo_cerrado_rechaza(monkeypatch):
    empresa, _, periodo, ruta, (inicio, fin) = contexto(monkeypatch)
    conciliador, _ = cliente_con_rol(ROL_CONCILIACION, empresas=(empresa,))
    coordinacion, _ = cliente_con_rol(ROL_COORDINACION_FINANCIERA, empresas=(empresa,))
    params = {"empresa_id": empresa}
    assert conciliador.post(ruta, params=params,
                            json={"tipo_wallet": "wiilog"}).status_code == 201
    rechazo = coordinacion.post(f"{ruta}/aprobar", params=params,
                               json={"motivo": "Faltan fechas"})
    assert rechazo.status_code == 422, rechazo.text
    with Session(engine()) as session:
        periodo_db = session.get(Periodo, periodo)
        periodo_db.cerrado = True
        session.commit()
    assert conciliador.post(ruta, params=params, json={"tipo_wallet": "pagos",
           "identidad_wallet": "pagos@sintetico.test", "vigente_desde": inicio,
           "vigente_hasta": fin}).status_code == 409
