"""Inventario global documental de O.C., sin atribución de empresa ni saldo."""
import uuid

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.main import app
from app.motores.cartera_ocs.drive_index import DocumentoDriveOC
from app.core.usuarios.roles import ROL_CONCILIACION
from tests.apoyo_auth import cliente, cliente_con_rol, cliente_superadmin, engine


def test_cartera_drive_ordenes_agrupa_archivos_y_limita_permisos():
    numero = str(uuid.uuid4().int % 900000 + 100000)
    oc = "GM" + numero
    distinta = "GM" + str((int(numero) + 1) % 900000 + 100000)
    id_pdf = "drive_pdf_" + uuid.uuid4().hex
    id_adj = "drive_adj_" + uuid.uuid4().hex
    id_sin = "drive_sin_" + uuid.uuid4().hex
    id_otro = "drive_otro_" + uuid.uuid4().hex
    file_ids = [id_pdf, id_adj, id_sin, id_otro]

    with Session(engine()) as db:
        db.add_all([
            DocumentoDriveOC(
                drive_file_id=id_pdf, drive_version="1",
                nombre_original=oc + "_antiguo.pdf", ruta_carpetas="Cliente / 2026",
                mime_type="application/pdf", numero_oc_candidato=oc,
                estado="SIN_ASIGNAR", empresa_id=None,
                modificado_drive="2026-10-01T10:00:00Z",
            ),
            DocumentoDriveOC(
                drive_file_id=id_pdf, drive_version="2",
                nombre_original=oc + "_actualizado.pdf", ruta_carpetas="Cliente / 2026",
                mime_type="application/pdf", numero_oc_candidato=oc,
                estado="SIN_ASIGNAR", empresa_id=None,
                modificado_drive="2026-10-20T10:00:00Z",
            ),
            DocumentoDriveOC(
                drive_file_id=id_adj, drive_version="1",
                nombre_original=oc + "_anexo.pdf", ruta_carpetas="Cliente / 2026",
                mime_type="application/pdf", numero_oc_candidato=oc,
                estado="SIN_ASIGNAR", empresa_id=None,
                modificado_drive="2026-10-19T10:00:00Z",
            ),
            DocumentoDriveOC(
                drive_file_id=id_sin, drive_version="1",
                nombre_original="anexo sin referencia.pdf", ruta_carpetas="Cliente",
                mime_type="application/pdf", numero_oc_candidato=None,
                estado="SIN_ASIGNAR", empresa_id=None,
            ),
            DocumentoDriveOC(
                drive_file_id=id_otro, drive_version="1",
                nombre_original=distinta + ".pdf", ruta_carpetas="Otro cliente",
                mime_type="application/pdf", numero_oc_candidato=distinta,
                estado="SIN_ASIGNAR", empresa_id=None,
            ),
        ])
        db.commit()

    try:
        admin = cliente_superadmin()
        listado = admin.get("/api/v1/cartera/ocs/drive/ordenes", params={"buscar": oc, "limit": 10})
        assert listado.status_code == 200, listado.text
        data = listado.json()
        assert data["total"] == 1
        assert data["items"][0]["numero_oc"] == oc
        assert data["items"][0]["soportes"] == 2
        assert data["items"][0]["estado"] == "SIN_VALIDAR"
        assert data["archivos_sin_oc"] >= 1
        assert data["archivos_vigentes"] >= 4

        soporte = admin.get(f"/api/v1/cartera/ocs/drive/ordenes/{oc}/soportes")
        assert soporte.status_code == 200
        assert soporte.json()["total"] == 2
        nombres = {x["nombre"] for x in soporte.json()["items"]}
        assert oc + "_actualizado.pdf" in nombres
        assert oc + "_anexo.pdf" in nombres
        assert oc + "_antiguo.pdf" not in nombres
        assert all(x["url_origen"].startswith("https://drive.google.com/file/d/") for x in soporte.json()["items"])
        assert all("empresa_id" not in x for x in soporte.json()["items"])

        assert admin.get("/api/v1/cartera/ocs/drive/ordenes/GMNO/soportes").status_code == 422
        assert admin.get("/api/v1/cartera/ocs/drive/ordenes/GM9999999/soportes").status_code == 422

        autorizado_por_empresa, _ = cliente_con_rol(ROL_CONCILIACION)
        assert autorizado_por_empresa.get("/api/v1/cartera/ocs/drive/ordenes").status_code == 403
        assert autorizado_por_empresa.get(
            f"/api/v1/cartera/ocs/drive/ordenes/{oc}/soportes"
        ).status_code == 403
        assert cliente().get("/api/v1/cartera/ocs/drive/ordenes").status_code == 401
    finally:
        with Session(engine()) as db:
            db.execute(delete(DocumentoDriveOC).where(DocumentoDriveOC.drive_file_id.in_(file_ids)))
            db.commit()


def test_vista_cartera_incluye_panel_documental_independiente_de_sheets():
    from fastapi.testclient import TestClient

    c = TestClient(app)
    pagina = c.get("/")
    modulo = c.get("/static/cartera_drive.js")
    appjs = c.get("/static/app.js")

    assert pagina.status_code == modulo.status_code == appjs.status_code == 200
    assert 'id="cartera-drive-panel"' in pagina.text
    assert 'id="cartera-drive-soportes"' in pagina.text
    assert 'src="/static/cartera_drive.js"' in pagina.text
    assert "/api/v1/cartera/ocs/drive/ordenes" in modulo.text
    assert 'sesion?.permisos?.["cartera.ver"] === "TODAS"' in modulo.text
    assert "textContent" in modulo.text
    assert "innerHTML" not in modulo.text
    assert "window.cargarCarteraDrive()" in appjs.text
    assert "if (!estadoFuente)" in appjs.text
