"""Almacenamiento privado de facturas y soportes, no servido como estático."""
import hashlib
import os
import tempfile
from pathlib import Path

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse

from .extraccion import extraer_ubl

MAX_BYTES = 10 * 1024 * 1024


async def leer_archivo(archivo: UploadFile, *, soporte: bool = False) -> tuple[bytes, str, str, str]:
    contenido = await archivo.read(MAX_BYTES + 1)
    nombre = archivo.filename or ""
    sufijo = Path(nombre).suffix.lower()
    if not contenido or len(contenido) > MAX_BYTES:
        raise HTTPException(422, "Archivo vacío o mayor a 10 MB.")
    tipos = {".pdf": ("application/pdf", b"%PDF-"),
             ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
             ".jpg": ("image/jpeg", b"\xff\xd8"),
             ".jpeg": ("image/jpeg", b"\xff\xd8")}
    if sufijo in tipos and contenido.startswith(tipos[sufijo][1]):
        tipo = tipos[sufijo][0]
    elif not soporte and sufijo == ".xml":
        try:
            extraer_ubl(contenido)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        tipo = "application/xml"
    else:
        raise HTTPException(422, "Formato inválido: PDF, PNG o JPG; XML UBL solo para facturas.")
    return contenido, hashlib.sha256(contenido).hexdigest(), sufijo, tipo


def base() -> Path:
    return Path(os.getenv("TESORERIA_DOCUMENTOS_DIR", "/data/tesoreria"))


def guardar(*, empresa_id: int, factura_id: int, contenido: bytes, sha: str,
            sufijo: str, pago_id: int | None = None) -> str:
    # Solo segmentos generados por el servidor: ningún nombre enviado por cliente.
    nombre = f"pago-{pago_id}-{sha}{sufijo}" if pago_id else f"factura-{sha}{sufijo}"
    ubicacion = Path(str(empresa_id)) / str(factura_id) / nombre
    destino = base() / ubicacion
    destino.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    # Las copias se respaldan por SHA: no se debe ver un archivo a medio escribir.
    # Publicación atómica, modo 0600 y fsync antes de que la DB pueda confirmar el registro.
    if destino.exists() or destino.is_symlink():
        raise FileExistsError("El documento ya existe en el volumen privado.")
    temporal = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=".carga-", dir=destino.parent, delete=False
        ) as f:
            temporal = Path(f.name)
            os.chmod(temporal, 0o600)
            f.write(contenido)
            f.flush()
            os.fsync(f.fileno())
        # La aplicación genera IDs únicos; reemplazar un archivo existente no está permitido.
        # os.link crea el nombre final solo si no existe y dentro del mismo filesystem.
        os.link(temporal, destino, follow_symlinks=False)
        descriptor = os.open(destino.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)
    return ubicacion.as_posix()


def eliminar(ubicacion: str | None) -> None:
    if ubicacion:
        (base() / ubicacion).unlink(missing_ok=True)


def descarga(ubicacion: str, tipo: str, nombre: str) -> FileResponse:
    carpeta = base().resolve()
    archivo = (carpeta / ubicacion).resolve()
    if not archivo.is_relative_to(carpeta) or not archivo.is_file():
        raise HTTPException(404, "Archivo no encontrado.")
    return FileResponse(archivo, media_type=tipo, filename=nombre, content_disposition_type="attachment")
