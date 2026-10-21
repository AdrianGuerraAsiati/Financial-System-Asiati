from dataclasses import dataclass

import pytest

from app.motores.cartera_ocs.drive_index import (
    DriveInventarioError,
    GoogleDriveInventario,
    numero_oc_candidato,
    validar_id,
)


def test_analiza_solo_referencia_inequivoca():
    assert numero_oc_candidato("GM629_ANDRES.pdf") == "GM629"
    assert numero_oc_candidato("GM-00535 (1).pdf") == "GM535"
    assert numero_oc_candidato("GM535 GM554.pdf") is None
    assert numero_oc_candidato("orden_sin_numero.pdf") is None


def test_rechaza_ids_con_inyeccion_de_consulta():
    with pytest.raises(ValueError):
        validar_id("abc' or trashed = true")


@dataclass
class Respuesta:
    payload: dict
    status_code: int = 200

    def json(self):
        return self.payload


class ClienteSimulado:
    def __init__(self):
        self.llamadas = []

    def get(self, url, *, params, timeout):
        self.llamadas.append(params)
        if "'folder_root_0001'" in params["q"]:
            if "pageToken" not in params:
                return Respuesta({
                    "nextPageToken": "pagina2",
                    "files": [
                        {"id": "folder_child_0002", "name": "2026",
                         "mimeType": "application/vnd.google-apps.folder"},
                        {"id": "file_pdf_0000001", "name": "GM629.pdf",
                         "mimeType": "application/pdf", "version": "1"},
                    ],
                })
            return Respuesta({"files": [
                {"id": "file_pdf_0000003", "name": "GM535.pdf",
                 "mimeType": "application/pdf", "version": "3"},
            ]})
        return Respuesta({"files": [
            {"id": "file_pdf_0000002", "name": "documento.pdf",
             "mimeType": "application/pdf", "version": "2"},
        ]})


def test_inventario_recursivo_paginado_y_rutas():
    cliente = ClienteSimulado()
    registros = GoogleDriveInventario(cliente).recorrer("folder_root_0001")
    assert len(registros) == 3
    assert {r.version for r in registros} == {"1", "2", "3"}
    assert next(r.ruta for r in registros if r.file_id == "file_pdf_0000002") == "2026"
    assert len(cliente.llamadas) == 3


def test_no_guarda_inventarios_parciales_si_se_agota_limite():
    cliente = ClienteSimulado()
    with pytest.raises(DriveInventarioError, match="límite de archivos"):
        GoogleDriveInventario(cliente).recorrer("folder_root_0001", max_archivos=1)


def test_errores_proveedor_no_exponen_credenciales():
    class ClienteDenegado:
        def get(self, url, *, params, timeout):
            return Respuesta({}, 403)
    with pytest.raises(DriveInventarioError, match="HTTP 403"):
        GoogleDriveInventario(ClienteDenegado()).recorrer("folder_root_0001")


def test_preflight_comprueba_carpeta_y_listado_sin_guardar():
    class ClientePreflight:
        def __init__(self):
            self.llamadas = []

        def get(self, url, *, params, timeout):
            self.llamadas.append((url, params))
            if url.endswith("/folder_root_0001"):
                return Respuesta({
                    "id": "folder_root_0001",
                    "mimeType": "application/vnd.google-apps.folder",
                    "trashed": False,
                })
            return Respuesta({"files": []})

    cliente = ClientePreflight()
    GoogleDriveInventario(cliente).verificar_acceso_raiz("folder_root_0001")
    assert len(cliente.llamadas) == 2
    assert cliente.llamadas[0][1]["fields"] == "id,mimeType,trashed"
    assert cliente.llamadas[1][1]["q"] == "'folder_root_0001' in parents and trashed = false"


def test_preflight_rechaza_falta_de_permiso_y_archivo_en_lugar_de_carpeta():
    class ClientePreflight:
        def __init__(self, codigo, mime):
            self.codigo = codigo
            self.mime = mime

        def get(self, url, *, params, timeout):
            return Respuesta({
                "id": "folder_root_0001",
                "mimeType": self.mime,
                "trashed": False,
            }, self.codigo)

    with pytest.raises(DriveInventarioError, match="HTTP 403"):
        GoogleDriveInventario(
            ClientePreflight(403, "application/vnd.google-apps.folder")
        ).verificar_acceso_raiz("folder_root_0001")

    with pytest.raises(DriveInventarioError, match="no es una carpeta activa"):
        GoogleDriveInventario(
            ClientePreflight(200, "application/pdf")
        ).verificar_acceso_raiz("folder_root_0001")

def test_modelo_documental_resuelve_empresa_en_proceso_cli_aislado():
    """La sincronización no importa app.main; debe registrar por sí misma la FK."""
    import subprocess
    import sys

    codigo = (
        "from app.motores.cartera_ocs.drive_index import DocumentoDriveOC; "
        "from app.core.db import Base; "
        "assert 'empresas' in Base.metadata.tables; "
        "assert {fk.column.table.name for fk in "
        "DocumentoDriveOC.__table__.c.empresa_id.foreign_keys} == {'empresas'}"
    )
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stderr
