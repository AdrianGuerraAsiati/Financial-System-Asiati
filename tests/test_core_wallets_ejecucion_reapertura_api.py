"""Control transaccional de ejecución de reapertura con PostgreSQL."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.periodos import Periodo
from app.core.periodos.history import PeriodoCierreEvento
from app.core.usuarios.roles import ROL_COORDINACION_FINANCIERA, ROL_SUPER_ADMINISTRADOR
from app.motores.conciliacion_wallets.solicitudes_reapertura import SolicitudReapertura
from app.motores.conciliacion_wallets.ejecucion_reapertura import EjecucionReapertura
from app.motores.conciliacion_wallets.revision_tardios import RevisionTardio
from app.motores.conciliacion_wallets.movimientos_tardios import MovimientoTardio
from app.motores.conciliacion_wallets.corte_operativo import CorteOperativo
from tests.apoyo_auth import SECRETO_PRUEBA, cliente_con_rol, crear_empresa, crear_periodo, engine

@pytest.fixture(autouse=True)
def auth(monkeypatch):
    monkeypatch.setenv("JWT_SECRET",SECRETO_PRUEBA)
    monkeypatch.setenv("AUTH_PROVIDER","local")

def test_ejecucion_requiere_aprobacion_y_deja_periodo_y_evento_auditado():
    empresa=crear_empresa("Ejecucion de reapertura")
    periodo=crear_periodo(empresa, cerrado=True)
    coord,coord_id=cliente_con_rol(ROL_COORDINACION_FINANCIERA,empresas=(empresa,))
    admin,admin_id=cliente_con_rol(ROL_SUPER_ADMINISTRADOR)
    otro_admin,_=cliente_con_rol(ROL_SUPER_ADMINISTRADOR)
    with Session(engine()) as session:
        p=session.get(Periodo,periodo)
        corte=CorteOperativo(empresa_id=empresa,periodo_id=periodo,
                            zona_horaria="America/Bogota",
                            corte_local=datetime.combine(p.fecha_fin,datetime.min.time()).replace(hour=23,minute=59,second=59),
                            corte_utc=datetime.now(timezone.utc),
                            registrado_por=coord_id,motivo="Prueba")
        session.add(corte)
        session.flush()
        mov=MovimientoTardio(empresa_id=empresa,periodo_id=periodo,corte_id=corte.id,
                            identificador_externo="ejecucion-uno",tipo_wallet="wiilog",identidad_wallet="",
                            instante_movimiento=datetime.now(timezone.utc),
                            instante_recepcion=datetime.now(timezone.utc),
                            clasificacion="POST_CORTE",evidencia_ref="prueba://mov",registrado_por=coord_id)
        session.add(mov)
        session.flush()
        rev=RevisionTardio(movimiento_id=mov.id,revisado_por=admin_id,
                           conclusion="REQUIERE_CORRECCION",justificacion="Incidencia",
                           evidencia_revision="prueba://rev",decision="AUTORIZAR_GESTION",
                           autorizado_por=coord_id,autorizado_at=datetime.now(timezone.utc),
                           justificacion_decision="Gestión")
        session.add(rev)
        session.flush()
        solicitud=SolicitudReapertura(empresa_id=empresa,periodo_id=periodo,
                                     revision_id=rev.id,solicitado_por=coord_id,
                                     motivo="Requiere corrección",evidencia_ref="prueba://sol")
        session.add(solicitud)
        session.commit()
        solicitud_id=solicitud.id
    url=f"/api/v1/wallets/periodos/{periodo}/solicitudes-reapertura/{solicitud_id}"
    params={"empresa_id":empresa}
    body={"motivo":"Corrección mediante expediente","plan_ref":"prueba://plan",
          "evidencia_previa_ref":"prueba://antes"}
    assert admin.post(f"{url}/ejecutar",params=params,json=body).status_code==422
    aprobado=admin.post(f"{url}/decidir",params=params,
                        json={"decision":"APROBADA","motivo":"Se autoriza reapertura"})
    assert aprobado.status_code==200,aprobado.text
    assert coord.post(f"{url}/ejecutar",params=params,json=body).status_code==403
    assert otro_admin.post(f"{url}/ejecutar",params=params,json=body).status_code==422
    ejecucion=admin.post(f"{url}/ejecutar",params=params,json=body)
    assert ejecucion.status_code==200,ejecucion.text
    assert ejecucion.json()["correccion_ejecutada"] is False
    assert admin.post(f"{url}/ejecutar",params=params,json=body).status_code==422
    with Session(engine()) as session:
        assert session.get(Periodo,periodo).cerrado is False
        registro=session.scalar(select(EjecucionReapertura).where(
            EjecucionReapertura.solicitud_id==solicitud_id))
        assert registro.ejecutado_por==admin_id
        eventos=list(session.scalars(select(PeriodoCierreEvento).where(
            PeriodoCierreEvento.periodo_id==periodo,
            PeriodoCierreEvento.accion=="REABRIR")))
        assert len(eventos)==1
