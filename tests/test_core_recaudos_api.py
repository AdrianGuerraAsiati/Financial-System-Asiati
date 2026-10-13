"""Integración con PostgreSQL: registro preliminar de ingresos reportados.

NO certifica créditos bancarios ni modifica cuentas por cobrar.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria.model import Auditoria
from app.core.usuarios.roles import (
    ROL_ANALISTA_TESORERIA, ROL_CONCILIACION, ROL_COORDINACION_FINANCIERA, ROL_TI,
)
from app.motores.recaudos.model import IngresoReportado
from tests.apoyo_auth import (
    cliente_con_rol, cliente_superadmin, crear_empresa, engine,
)


def _payload(empresa_id: int, referencia: str = "ABONO-2026-XYZ", **kwargs) -> dict:
    return {
        "empresa_id": empresa_id,
        "fecha_reportada": "2026-10-13",
        "monto": "1040.25",
        "moneda": "COP",
        "cuenta_receptora": "BANCOLOMBIA 7401",
        "referencia_origen": referencia,
        "pagador_reportado": "Cliente reportado",
        "descripcion": "Abono por verificar",
        **kwargs,
    }


def test_registro_manual_nunca_verifica_ni_aplica_y_audita() -> None:
    empresa = crear_empresa("Registro recaudos")
    cliente = cliente_superadmin()
    r = cliente.post("/api/v1/recaudos/ingresos", json=_payload(empresa))
    assert r.status_code == 201, r.text
    ingreso = r.json()
    assert ingreso["empresa_id"] == empresa
    assert ingreso["estado"] == "PENDIENTE_VERIFICACION"
    assert ingreso["aplicado_a_cartera"] is False
    assert ingreso["verificado_con_banco"] is False
    assert ingreso["origen"] == "MANUAL"
    assert ingreso["monto_reportado"] == "1040.25"
    assert ingreso["fecha_reportada"] == "2026-10-13"

    detalle = cliente.get("/api/v1/recaudos/ingresos/" + str(ingreso["id"]))
    assert detalle.status_code == 200
    assert detalle.json()["referencia_origen"] == "ABONO-2026-XYZ"
    assert cliente.patch("/api/v1/recaudos/ingresos/" + str(ingreso["id"]),
                         json={"estado": "CONCILIADO"}).status_code == 405

    with Session(engine()) as s:
        guardado = s.get(IngresoReportado, ingreso["id"])
        assert guardado is not None
        assert guardado.monto == Decimal("1040.25")
        assert guardado.estado == "PENDIENTE_VERIFICACION"
        auditoria = s.scalar(select(Auditoria).where(
            Auditoria.entidad == "ingreso_reportado",
            Auditoria.entidad_id == guardado.id,
            Auditoria.accion == "recaudos.ingreso_reportado.crear",
        ))
        assert auditoria is not None
        assert auditoria.empresa_id == empresa


def test_referencia_duplicada_por_cuenta_y_empresa() -> None:
    empresa = crear_empresa("Duplicados recaudos")
    cliente = cliente_superadmin()
    a = cliente.post("/api/v1/recaudos/ingresos", json=_payload(empresa, referencia="  ABONO   077  "))
    assert a.status_code == 201, a.text
    b = cliente.post("/api/v1/recaudos/ingresos", json=_payload(
        empresa, referencia="abono 077", cuenta_receptora="bancolombia 7401"))
    assert b.status_code == 409
    c = cliente.post("/api/v1/recaudos/ingresos", json=_payload(
        empresa, referencia="ABONO 077", cuenta_receptora="BANCOLOMBIA OTRA CUENTA"))
    assert c.status_code == 201, c.text
    otro = crear_empresa("Otra empresa recaudos")
    d = cliente.post("/api/v1/recaudos/ingresos", json=_payload(otro, referencia="ABONO 077"))
    assert d.status_code == 201, d.text


def test_bandeja_paginada_y_filtros_por_empresa() -> None:
    empresa = crear_empresa("Bandeja recaudos")
    cliente = cliente_superadmin()
    for n in range(4):
        r = cliente.post("/api/v1/recaudos/ingresos", json=_payload(
            empresa, referencia=f"TRX-{n}", monto=str(100 + n),
            moneda="USD" if n == 3 else "COP",
            fecha_reportada="2026-10-11" if n < 2 else "2026-10-13"))
        assert r.status_code == 201, r.text
    p = cliente.get("/api/v1/recaudos/ingresos", params={
        "empresa_id": empresa, "limite": 2, "desde": 0,
    })
    assert p.status_code == 200, p.text
    assert p.json()["total"] == 4
    assert len(p.json()["items"]) == 2
    siguiente = cliente.get("/api/v1/recaudos/ingresos", params={
        "empresa_id": empresa, "limite": 2, "desde": 2,
    })
    assert siguiente.status_code == 200
    assert len({x["id"] for x in p.json()["items"] + siguiente.json()["items"]}) == 4
    solo_dolares = cliente.get("/api/v1/recaudos/ingresos", params={
        "empresa_id": empresa, "moneda": "USD",
    })
    assert solo_dolares.json()["total"] == 1
    search = cliente.get("/api/v1/recaudos/ingresos", params={
        "empresa_id": empresa, "buscar": "trx-0",
    })
    assert search.json()["total"] == 1
    rango = cliente.get("/api/v1/recaudos/ingresos", params={
        "empresa_id": empresa, "desde_fecha": "2026-10-13",
    })
    assert rango.json()["total"] == 2
    assert cliente.get("/api/v1/recaudos/ingresos", params={
        "empresa_id": empresa, "desde_fecha": "2026-10-13", "hasta_fecha": "2026-10-12",
    }).status_code == 422
    assert cliente.get("/api/v1/recaudos/ingresos", params={
        "empresa_id": empresa, "limite": 101,
    }).status_code == 422


def test_validaciones_importes_y_campo_estado_inyectado() -> None:
    empresa = crear_empresa("Entrada invalida recaudos")
    cliente = cliente_superadmin()
    for monto in ("0", "-3", "2.005", "NaN", "Infinity", "abc"):
        r = cliente.post("/api/v1/recaudos/ingresos", json=_payload(empresa, monto=monto))
        assert r.status_code == 422, (monto, r.text)
    for campo, valor in (("cuenta_receptora", "    "), ("referencia_origen", "  "),
                         ("estado", "CONCILIADO"), ("origen", "BANCO_CONFIRMADO")):
        r = cliente.post("/api/v1/recaudos/ingresos", json=_payload(empresa, **{campo: valor}))
        assert r.status_code == 422, (campo, r.text)
    resultado = cliente.get("/api/v1/recaudos/ingresos", params={"empresa_id": empresa})
    assert resultado.json()["total"] == 0


def test_permisos_lectura_ti_coordinacion_y_escritura_solo_analista() -> None:
    empresa = crear_empresa("Permisos recaudos")
    analista, _ = cliente_con_rol(ROL_ANALISTA_TESORERIA, empresas=(empresa,))
    creado = analista.post("/api/v1/recaudos/ingresos", json=_payload(empresa))
    assert creado.status_code == 201, creado.text

    coord, _ = cliente_con_rol(ROL_COORDINACION_FINANCIERA, empresas=(empresa,))
    assert coord.get("/api/v1/recaudos/ingresos", params={"empresa_id": empresa}).status_code == 200
    assert coord.post("/api/v1/recaudos/ingresos", json=_payload(empresa, referencia="COORD")).status_code == 403

    ti, _ = cliente_con_rol(ROL_TI)
    assert ti.get("/api/v1/recaudos/ingresos", params={"empresa_id": empresa}).status_code == 200
    assert ti.post("/api/v1/recaudos/ingresos", json=_payload(empresa, referencia="TI")).status_code == 403

    conciliador, _ = cliente_con_rol(ROL_CONCILIACION, empresas=(empresa,))
    assert conciliador.get("/api/v1/recaudos/ingresos", params={"empresa_id": empresa}).status_code == 403
    assert conciliador.post("/api/v1/recaudos/ingresos", json=_payload(empresa, referencia="CONC")).status_code == 403


def test_empresa_no_asignada_no_se_revela_por_id_ni_por_bandeja() -> None:
    propia = crear_empresa("Propia recaudos")
    ajena = crear_empresa("Ajena recaudos")
    cliente = cliente_superadmin()
    id_ajeno = cliente.post("/api/v1/recaudos/ingresos", json=_payload(ajena)).json()["id"]
    analista, _ = cliente_con_rol(ROL_ANALISTA_TESORERIA, empresas=(propia,))
    assert analista.get("/api/v1/recaudos/ingresos", params={"empresa_id": ajena}).status_code == 404
    assert analista.get("/api/v1/recaudos/ingresos/" + str(id_ajeno)).status_code == 404
    assert analista.post("/api/v1/recaudos/ingresos", json=_payload(ajena)).status_code == 404
    assert analista.get("/api/v1/recaudos/ingresos", params={"empresa_id": propia}).status_code == 200
