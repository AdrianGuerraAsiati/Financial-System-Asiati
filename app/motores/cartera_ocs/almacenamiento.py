import re
from pathlib import Path
from typing import Protocol


class AlmacenComprobantes(Protocol):
    def guardar(
        self,
        *,
        empresa_id: int,
        oc: str,
        nombre_archivo: str,
        contenido_hash: str,
        contenido: bytes,
    ) -> str: ...

    def leer(self, ubicacion: str) -> bytes: ...

    def eliminar(self, ubicacion: str) -> None: ...


def _segmento_seguro(valor: str, *, fallback: str) -> str:
    limpio = re.sub(r"[^A-Za-z0-9._-]+", "_", valor.strip())
    limpio = limpio.strip("._")
    return limpio or fallback


class AlmacenLocalComprobantes:
    """Adaptador local reemplazable para almacenar archivos de comprobantes."""

    def __init__(self, directorio_base: str | Path) -> None:
        self.directorio_base = Path(directorio_base)

    def guardar(
        self,
        *,
        empresa_id: int,
        oc: str,
        nombre_archivo: str,
        contenido_hash: str,
        contenido: bytes,
    ) -> str:
        nombre_base = Path(nombre_archivo).name
        nombre_seguro = _segmento_seguro(
            nombre_base,
            fallback="comprobante.bin",
        )
        oc_segura = _segmento_seguro(oc, fallback="sin-oc")

        ubicacion = (
            Path(str(empresa_id))
            / oc_segura
            / f"{contenido_hash}-{nombre_seguro}"
        )
        destino = self.directorio_base / ubicacion
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(contenido)

        return ubicacion.as_posix()

    def _resolver(self, ubicacion: str) -> Path:
        base = self.directorio_base.resolve()
        destino = (base / ubicacion).resolve()
        try:
            destino.relative_to(base)
        except ValueError as exc:
            raise ValueError(
                "La ubicación del comprobante está fuera del almacenamiento permitido."
            ) from exc
        return destino

    def leer(self, ubicacion: str) -> bytes:
        return self._resolver(ubicacion).read_bytes()

    def eliminar(self, ubicacion: str) -> None:
        destino = self._resolver(ubicacion)
        try:
            destino.unlink()
        except FileNotFoundError:
            return
