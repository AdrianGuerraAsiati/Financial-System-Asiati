"""Pruebas sintéticas del respaldo documental; no acceden a archivos financieros reales."""
from hashlib import sha256
from io import BytesIO
import os
from pathlib import Path
import tarfile

import pytest

from app.motores.tesoreria.storage import guardar
from ops.tesoreria_archivos import crear, inspeccionar


def _nombre(empresa: int, factura: int, datos: bytes) -> str:
    return f"{empresa}/{factura}/factura-{sha256(datos).hexdigest()}.pdf"


def _archivo(root: Path, nombre: str, datos: bytes) -> Path:
    ruta = root / nombre
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(datos)
    return ruta


def test_archivo_valido_se_respalda_se_verifica_y_se_restaura_aislado(tmp_path: Path):
    original = tmp_path / "original"
    original.mkdir()
    contenido = b"%PDF-1.4\ncontenido de prueba sin informacion financiera"
    nombre = _nombre(1, 22, contenido)
    _archivo(original, nombre, contenido)
    salida = BytesIO()
    assert crear(original, salida) == 1
    archive = tmp_path / "respaldo.tar.gz"
    archive.write_bytes(salida.getvalue())
    firma = sha256(archive.read_bytes()).hexdigest()
    assert inspeccionar(archive, firma) == 1
    destino = tmp_path / "tesoreria-restore-pruebas"
    assert inspeccionar(archive, firma, destino) == 1
    assert (destino / nombre).read_bytes() == contenido
    assert not (original / "1" / "23").exists()


def test_archivo_con_hash_incorrecto_no_se_respalda(tmp_path: Path):
    original = tmp_path / "original"
    original.mkdir()
    _archivo(original, _nombre(2, 33, b"correcto"), b"contenido alterado")
    with pytest.raises(ValueError, match="hash"):
        crear(original, BytesIO())


def test_restaurar_rechaza_sha_incorrecto_y_destino_activo(tmp_path: Path):
    original = tmp_path / "original"
    original.mkdir()
    _archivo(original, _nombre(1, 3, b"datos"), b"datos")
    salida = BytesIO()
    crear(original, salida)
    path = tmp_path / "backup.tar.gz"
    path.write_bytes(salida.getvalue())
    sha = sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="SHA256"):
        inspeccionar(path, "0" * 64)
    with pytest.raises(ValueError, match="tesoreria-restore"):
        inspeccionar(path, sha, tmp_path / "volumen-activo")
    no_vacio = tmp_path / "tesoreria-restore-lleno"
    no_vacio.mkdir()
    (no_vacio / "archivo").write_bytes(b"existente")
    with pytest.raises(ValueError, match="vacío"):
        inspeccionar(path, sha, no_vacio)


@pytest.mark.parametrize("nombre", ["../../fuera.pdf", "/root/privado.pdf",
    "1/2/../../fuera.pdf", "1/2/otro.pdf", "1/2/pago-3-" + "a" * 64 + ".xml"])
def test_tar_inseguro_se_rechaza(tmp_path: Path, nombre: str):
    path = tmp_path / "malicioso.tar.gz"
    with tarfile.open(path, "w:gz") as tar:
        data = b"malicioso"
        info = tarfile.TarInfo(nombre)
        info.size = len(data)
        tar.addfile(info, BytesIO(data))
    sha = sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="contrato|insegura|XML"):
        inspeccionar(path, sha)


def test_tar_symlink_se_rechaza(tmp_path: Path):
    path = tmp_path / "enlace.tar.gz"
    with tarfile.open(path, "w:gz") as tar:
        info = tarfile.TarInfo("1/2/factura-" + "a" * 64 + ".pdf")
        info.type = tarfile.SYMTYPE
        info.linkname = "/etc/passwd"
        tar.addfile(info)
    with pytest.raises(ValueError, match="no regular"):
        inspeccionar(path, sha256(path.read_bytes()).hexdigest())


def test_guardar_es_atomico_y_no_reemplaza_documentos(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TESORERIA_DOCUMENTOS_DIR", str(tmp_path))
    payload = b"%PDF-1.4\nprueba guardada"
    firma = sha256(payload).hexdigest()
    relativo = guardar(empresa_id=10, factura_id=22, contenido=payload,
                       sha=firma, sufijo=".pdf")
    ruta = tmp_path / relativo
    assert ruta.read_bytes() == payload
    assert (ruta.stat().st_mode & 0o777) == 0o600
    assert not list(tmp_path.rglob(".carga-*"))
    with pytest.raises(FileExistsError):
        guardar(empresa_id=10, factura_id=22, contenido=b"cambio", sha=firma, sufijo=".pdf")
    assert ruta.read_bytes() == payload


def test_backup_no_sigue_enlaces_simbolicos(tmp_path: Path):
    root = tmp_path / "documentos"
    root.mkdir()
    (root / "1").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="enlazados"):
        crear(root, BytesIO())
