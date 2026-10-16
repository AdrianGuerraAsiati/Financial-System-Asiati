"""Avisos de facturas vencidas/por vencer: solo lectura y aislamiento multiempresa."""
from datetime import date, timedelta

from app.core.usuarios.roles import ROL_ANALISTA_TESORERIA, ROL_TI
from tests.apoyo_auth import cliente_con_rol, cliente_superadmin, crear_empresa
from tests.test_core_tesoreria_tablero import abono, factura


def test_avisos_incluyen_abonos_pendientes_y_monedas_sin_mezclar(tmp_path, monkeypatch):
    monkeypatch.setenv("TESORERIA_DOCUMENTOS_DIR", str(tmp_path))
    hoy = date.today()
    cliente = cliente_superadmin()
    propia = crear_empresa("Facturas avisos propia")
    ajena = crear_empresa("Facturas avisos ajena")

    vencida = factura(cliente, propia, "VENC-01", "1000.00", hoy - timedelta(days=2))
    hoy_pago = factura(cliente, propia, "HOY-02", "300.00", hoy)
    limite = factura(cliente, propia, "LIM-03", "400.00", hoy + timedelta(days=7))
    parcial = factura(cliente, propia, "PAR-04", "900.00", hoy + timedelta(days=2))
    otra_moneda = factura(cliente, propia, "USD-05", "89.99", hoy + timedelta(days=1), moneda="USD")
    saldada = factura(cliente, propia, "PAG-06", "150.00", hoy - timedelta(days=5))
    factura(cliente, propia, "FUT-07", "100.00", hoy + timedelta(days=8))
    factura(cliente, propia, "SIN-08", "100.00", None)
    factura(cliente, ajena, "AJENA-09", "200.00", hoy - timedelta(days=3))
    abono(cliente, parcial["id"], "200.00", hoy, "PAR-AVISO")
    abono(cliente, saldada["id"], "150.00", hoy, "TOT-AVISO")

    r = cliente.get("/api/v1/tesoreria/notificaciones", params={"empresa_id": propia})
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "no-store"
    resultado = r.json()
    assert resultado["total"] == 5
    assert resultado["vencidas"] == 1
    assert resultado["por_vencer"] == 4
    assert resultado["horizonte_dias"] == 7
    assert resultado["fecha_corte"] == hoy.isoformat()
    assert not resultado["hay_mas"]
    ids = {item["id"] for item in resultado["items"]}
    assert ids == {vencida["id"], hoy_pago["id"], limite["id"], parcial["id"], otra_moneda["id"]}
    assert resultado["items"][0]["id"] == vencida["id"]
    assert next(item for item in resultado["items"] if item["id"] == parcial["id"])["saldo"] == "700.00"
    assert next(item for item in resultado["items"] if item["id"] == limite["id"])["dias_para_vencer"] == 7
    assert next(item for item in resultado["items"] if item["id"] == vencida["id"])["tipo"] == "VENCIDA"
    assert {item["moneda"] for item in resultado["items"]} == {"COP", "USD"}


def test_avisos_separados_por_empresa_y_permisos(tmp_path, monkeypatch):
    monkeypatch.setenv("TESORERIA_DOCUMENTOS_DIR", str(tmp_path))
    propia = crear_empresa("Empresa privada Facturación")
    ajena = crear_empresa("Empresa bloqueada Facturación")
    superadmin = cliente_superadmin()
    factura(superadmin, propia, "FAC-PROP", "200", date.today())
    factura(superadmin, ajena, "FAC-AJENA", "300", date.today())

    analista, _ = cliente_con_rol(ROL_ANALISTA_TESORERIA, empresas=(propia,))
    resp = analista.get("/api/v1/tesoreria/notificaciones", params={"empresa_id": propia})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["numero"] == "FAC-PROP"

    assert analista.get("/api/v1/tesoreria/notificaciones",
                        params={"empresa_id": ajena}).status_code == 404
    ti, _ = cliente_con_rol(ROL_TI)
    assert ti.get("/api/v1/tesoreria/notificaciones",
                  params={"empresa_id": propia}).status_code == 200
    assert superadmin.get("/api/v1/tesoreria/notificaciones").status_code == 422
