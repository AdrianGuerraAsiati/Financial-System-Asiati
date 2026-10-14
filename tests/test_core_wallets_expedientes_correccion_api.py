"""API de expedientes: sesiones, rol y aislamiento con PostgreSQL."""
import pytest
from tests.apoyo_auth import SECRETO_PRUEBA, cliente, cliente_con_rol, crear_empresa, crear_periodo
from app.core.usuarios.roles import ROL_CONCILIACION, ROL_COORDINACION_FINANCIERA

@pytest.fixture(autouse=True)
def _auth(monkeypatch):
    monkeypatch.setenv("JWT_SECRET",SECRETO_PRUEBA)
    monkeypatch.setenv("AUTH_PROVIDER","local")

def test_permiso_y_empresa_de_expedientes():
    empresa=crear_empresa("Expedientes test")
    periodo=crear_periodo(empresa)
    ruta=f"/api/v1/wallets/periodos/{periodo}/expedientes-correccion"
    datos={"ejecucion_id":999999,"carga_id":999999,"movimiento_ref":"mov-prueba",
           "valor_anterior":"100.00","valor_propuesto":"101.00",
           "evidencia_antes_ref":"test://antes","evidencia_despues_ref":"test://despues",
           "justificacion":"Solo prueba"}
    assert cliente().post(ruta,params={"empresa_id":empresa},json=datos).status_code==401
    conciliacion,_=cliente_con_rol(ROL_CONCILIACION,empresas=(empresa,))
    finanzas,_=cliente_con_rol(ROL_COORDINACION_FINANCIERA,empresas=(empresa,))
    assert finanzas.post(ruta,params={"empresa_id":empresa},json=datos).status_code==403
    assert conciliacion.post(ruta,params={"empresa_id":empresa+999999},json=datos).status_code==404
    assert conciliacion.post(ruta,params={"empresa_id":empresa},json=datos).status_code==404
    assert conciliacion.get(ruta,params={"empresa_id":empresa}).status_code==200
