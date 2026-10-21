"""Ordenamiento cronológico global del índice de O.C. documentales."""
import uuid

from sqlalchemy import delete
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.motores.cartera_ocs.drive_api import _ordenar_ordenes_documentales
from app.motores.cartera_ocs.drive_index import DocumentoDriveOC
from tests.apoyo_auth import cliente_con_rol, cliente_superadmin, engine
from app.core.usuarios.roles import ROL_CONCILIACION


def test_fechas_ordena_antes_de_paginar_y_fechas_ausentes_al_final():
    items = [
        {"numero_oc": "GM9", "ultima_modificacion": None},
        {"numero_oc": "GM3", "ultima_modificacion": "2026-09-14T00:00:00Z"},
        {"numero_oc": "GM1", "ultima_modificacion": "2026-10-01T12:00:00-05:00"},
        {"numero_oc": "GM2", "ultima_modificacion": "2026-10-01T16:00:00Z"},
        {"numero_oc": "GM4", "ultima_modificacion": "2026-10-01T16:00:00Z"},
        {"numero_oc": "GM8", "ultima_modificacion": "fecha inválida"},
    ]
    recientes = _ordenar_ordenes_documentales(items, "fecha_desc")
    assert [x["numero_oc"] for x in recientes] == [
        "GM1", "GM2", "GM4", "GM3", "GM8", "GM9"
    ]
    antiguas = _ordenar_ordenes_documentales(items, "fecha_asc")
    assert [x["numero_oc"] for x in antiguas] == [
        "GM3", "GM2", "GM4", "GM1", "GM8", "GM9"
    ]
    alfabeticas = _ordenar_ordenes_documentales(items, "oc_asc")
    assert [x["numero_oc"] for x in alfabeticas] == [
        "GM1", "GM2", "GM3", "GM4", "GM8", "GM9"
    ]
    assert items[0]["numero_oc"] == "GM9"  # No altera la lista original.


def test_api_ordena_todas_las_oc_antes_del_offset_y_restringe_acceso():
    prefijo = str(uuid.uuid4().int % 8000 + 1000)
    ocs = ["GM" + prefijo + sufijo for sufijo in ("1", "2", "3", "4")]
    fechas = [
        "2024-02-01T08:00:00Z",
        "2026-10-20T09:00:00Z",
        "2025-01-01T09:00:00Z",
        None,
    ]
    ids = []
    with Session(engine()) as db:
        for idx, (oc, fecha) in enumerate(zip(ocs, fechas)):
            fid = "drive_orden_" + uuid.uuid4().hex
            ids.append(fid)
            db.add(DocumentoDriveOC(
                drive_file_id=fid,
                drive_version="1",
                nombre_original=oc + ".pdf",
                ruta_carpetas="prueba cronológica",
                mime_type="application/pdf",
                numero_oc_candidato=oc,
                estado="SIN_ASIGNAR",
                empresa_id=None,
                modificado_drive=fecha,
            ))
        db.commit()

    try:
        client = cliente_superadmin()
        url = "/api/v1/cartera/ocs/drive/ordenes"
        base = {"buscar": "GM" + prefijo, "limit": 2}
        primera = client.get(url, params={**base, "orden": "fecha_desc", "offset": 0})
        segunda = client.get(url, params={**base, "orden": "fecha_desc", "offset": 2})
        assert primera.status_code == segunda.status_code == 200
        assert primera.json()["total"] == 4
        assert primera.json()["orden"] == "fecha_desc"
        assert [x["numero_oc"] for x in primera.json()["items"]] == [ocs[1], ocs[2]]
        assert [x["numero_oc"] for x in segunda.json()["items"]] == [ocs[0], ocs[3]]

        asc = client.get(url, params={**base, "orden": "fecha_asc", "limit": 10})
        assert asc.status_code == 200
        assert [x["numero_oc"] for x in asc.json()["items"]] == [
            ocs[0], ocs[2], ocs[1], ocs[3]
        ]

        defecto = client.get(url, params={**base, "limit": 10})
        assert defecto.status_code == 200
        assert defecto.json()["orden"] == "oc_asc"
        assert [x["numero_oc"] for x in defecto.json()["items"]] == ocs

        assert client.get(url, params={"orden": "id_desc"}).status_code == 422
        restringido, _ = cliente_con_rol(ROL_CONCILIACION)
        assert restringido.get(url, params={"orden": "fecha_desc"}).status_code == 403
    finally:
        with Session(engine()) as db:
            db.execute(
                delete(DocumentoDriveOC).where(DocumentoDriveOC.drive_file_id.in_(ids))
            )
            db.commit()


def test_interfaz_envia_orden_al_servidor_y_reinicia_paginacion():
    client = TestClient(app)
    pagina = client.get("/").text
    js = client.get("/static/cartera_drive.js").text
    assert 'id="cartera-drive-orden"' in pagina
    for opcion in ("fecha_desc", "fecha_asc", "oc_asc"):
        assert 'value="' + opcion + '"' in pagina
    assert "orden: orden.value" in js
    assert 'orden.addEventListener("change"' in js
    assert "offset + limite < total" in js
    assert "offset + LIMITE < total" not in js
