"""PostgreSQL: la API requiere identidad autenticada y alcance de empresa."""
import pytest
from tests.apoyo_auth import SECRETO_PRUEBA, cliente, cliente_con_rol, crear_empresa, crear_periodo
from app.core.usuarios.roles import ROL_CONCILIACION, ROL_COORDINACION_FINANCIERA

@pytest.fixture(autouse=True)
def auth(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRETO_PRUEBA)
    monkeypatch.setenv("AUTH_PROVIDER", "local")

def test_solicitud_requiere_rol_y_empresa():
    empresa=crear_empresa("Solicitudes")
    periodo=crear_periodo(empresa, cerrado=True)
    url=f"/api/v1/wallets/periodos/{periodo}/solicitudes-reapertura"
    datos={"revision_id":1,"motivo":"Prueba sintética","evidencia_ref":"prueba://1"}
    assert cliente().post(url,params={"empresa_id":empresa},json=datos).status_code==401
    conciliador,_=cliente_con_rol(ROL_CONCILIACION,empresas=(empresa,))
    assert conciliador.post(url,params={"empresa_id":empresa},json=datos).status_code==403
    coordinacion,_=cliente_con_rol(ROL_COORDINACION_FINANCIERA,empresas=(empresa,))
    ajena=crear_empresa("Otra empresa")
    assert coordinacion.post(url,params={"empresa_id":ajena},json=datos).status_code==404
    assert coordinacion.post(url,params={"empresa_id":empresa},json=datos).status_code==404
