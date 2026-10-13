#!/usr/bin/env python3
"""Respaldo/restauración aislada de documentos de Tesorería. Solo stdlib.

El archivo tar.gz contiene rutas <empresa>/<factura>/<tipo>-<sha256>.<ext>.
Nunca recupera directamente al volumen activo; restaurar exige staging vacío.
No incluye secretos ni metadatos de PostgreSQL; deben conservarse por separado.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import sys
import tarfile

DOCUMENTO = re.compile(
    r"([1-9][0-9]*)/([1-9][0-9]*)/"
    r"(?:factura|pago-[1-9][0-9]*)-([0-9a-f]{64})\.(pdf|png|jpe?g|xml)$"
)
MAX_ARCHIVO = 10 * 1024 * 1024
MAX_DOCUMENTOS = 500_000
MAX_TOTAL = 500 * 1024 * 1024 * 1024


def _hash(stream) -> str:
    h = hashlib.sha256()
    for bloque in iter(lambda: stream.read(1024 * 1024), b""):
        h.update(bloque)
    return h.hexdigest()


def _validar_nombre(nombre: str) -> str:
    if not isinstance(nombre, str) or "\\" in nombre or nombre.startswith("/"):
        raise ValueError("Ruta de documento insegura.")
    m = DOCUMENTO.fullmatch(nombre)
    if not m:
        raise ValueError("Ruta de documento fuera del contrato de Tesorería.")
    if nombre.rsplit("/", 1)[-1].startswith("pago-") and m.group(4) == "xml":
        raise ValueError("Un comprobante de pago no puede ser XML.")
    return m.group(3)


def _listar_documentos(raiz: Path) -> list[tuple[str, Path]]:
    if not raiz.is_dir() or raiz.is_symlink():
        raise ValueError("El volumen debe existir y no puede ser un enlace simbólico.")
    documentos = []
    for actual, directorios, archivos in os.walk(raiz, followlinks=False):
        for directorio in directorios:
            if (Path(actual) / directorio).is_symlink():
                raise ValueError("Los directorios enlazados están prohibidos.")
        for archivo in archivos:
            ruta = Path(actual) / archivo
            if ruta.is_symlink() or not ruta.is_file():
                raise ValueError("Tipo de documento no permitido.")
            relativo = ruta.relative_to(raiz).as_posix()
            _validar_nombre(relativo)
            if ruta.stat().st_size > MAX_ARCHIVO:
                raise ValueError("El archivo supera el tamaño máximo de la aplicación.")
            documentos.append((relativo, ruta))
            if len(documentos) > MAX_DOCUMENTOS:
                raise ValueError("Demasiados documentos para el respaldo.")
    return sorted(documentos)


def crear(raiz: Path, salida) -> int:
    documentos = _listar_documentos(raiz)
    with tarfile.open(fileobj=salida, mode="w|gz", format=tarfile.PAX_FORMAT) as tar:
        for nombre, ruta in documentos:
            esperado = _validar_nombre(nombre)
            with ruta.open("rb") as origen:
                if _hash(origen) != esperado:
                    raise ValueError("Documento con hash distinto a su nombre; no se respalda.")
                origen.seek(0)
                tamano = ruta.stat().st_size
                info = tarfile.TarInfo(nombre)
                info.size = tamano
                info.mode = 0o600
                info.mtime = int(ruta.stat().st_mtime)
                tar.addfile(info, origen)
                if ruta.stat().st_size != tamano:
                    raise ValueError("Documento modificado durante el respaldo.")
    return len(documentos)


def _validar_archivo(archivo: Path, hash_esperado: str) -> None:
    if not archivo.is_file() or archivo.is_symlink():
        raise ValueError("El respaldo solicitado no existe o es un enlace.")
    if not re.fullmatch("[0-9a-f]{64}", hash_esperado):
        raise ValueError("Se requiere SHA256 esperado de 64 dígitos.")
    with archivo.open("rb") as f:
        if _hash(f) != hash_esperado:
            raise ValueError("El SHA256 del respaldo no coincide con el manifiesto.")


def inspeccionar(archivo: Path, hash_esperado: str, destino: Path | None = None) -> int:
    _validar_archivo(archivo, hash_esperado)
    # Nunca extraer sobre el volumen activo. La operación es un staging manual.
    if destino is not None:
        if not destino.is_absolute() or not destino.name.startswith("tesoreria-restore-"):
            raise ValueError("La restauración exige una ruta absoluta tesoreria-restore-*.")
        if destino.is_symlink() or (destino.exists() and (not destino.is_dir() or any(destino.iterdir()))):
            raise ValueError("El destino de restauración debe estar vacío y no ser un enlace.")
        destino.mkdir(mode=0o700, parents=True, exist_ok=True)
        destino = destino.resolve()
    vistos = set()
    bytes_totales = 0
    with tarfile.open(archivo, mode="r:gz") as tar:
        for miembro in tar:
            if not miembro.isfile():
                raise ValueError("El respaldo contiene un miembro no regular.")
            esperado = _validar_nombre(miembro.name)
            if miembro.name in vistos:
                raise ValueError("Hay nombres repetidos en el respaldo.")
            vistos.add(miembro.name)
            if len(vistos) > MAX_DOCUMENTOS:
                raise ValueError("Exceso de documentos en el respaldo.")
            bytes_totales += miembro.size
            if miembro.size > MAX_ARCHIVO or bytes_totales > MAX_TOTAL:
                raise ValueError("Los tamaños declarados exceden los límites.")
            origen = tar.extractfile(miembro)
            if origen is None:
                raise ValueError("El miembro del respaldo no es legible.")
            if destino is not None:
                ruta = destino / miembro.name
                ruta.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
                with ruta.open("xb") as f:
                    h = hashlib.sha256()
                    while True:
                        parte = origen.read(1024 * 1024)
                        if not parte:
                            break
                        h.update(parte)
                        f.write(parte)
                    f.flush()
                    os.fsync(f.fileno())
                actual = h.hexdigest()
            else:
                actual = _hash(origen)
            if actual != esperado:
                raise ValueError("Documento corrupto: el contenido no coincide con el hash.")
    return len(vistos)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operacion", required=True)
    nuevo = sub.add_parser("crear")
    nuevo.add_argument("--root", type=Path, required=True)
    chequear = sub.add_parser("verificar")
    chequear.add_argument("--archive", type=Path, required=True)
    chequear.add_argument("--sha256", required=True)
    reponer = sub.add_parser("restaurar")
    reponer.add_argument("--archive", type=Path, required=True)
    reponer.add_argument("--sha256", required=True)
    reponer.add_argument("--dest", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.operacion == "crear":
            cuenta = crear(args.root, sys.stdout.buffer)
        else:
            cuenta = inspeccionar(args.archive, args.sha256,
                                 args.dest if args.operacion == "restaurar" else None)
    except (ValueError, OSError, tarfile.TarError) as exc:
        print(f"Operación detenida: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Operación documental completada: {cuenta} archivos.", file=sys.stderr)


if __name__ == "__main__":
    main()
