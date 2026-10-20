"""Inventario de O.C. en Drive: metadata de solo lectura y revisión humana.

No asigna una empresa ni genera cartera automáticamente. Ningún PDF se expone
desde este módulo; su descarga y lectura se incorporarán en una fase posterior.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import os
import re
from typing import Protocol

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base


DRIVE_ID = re.compile(r"^[A-Za-z0-9_-]{10,150}$")
OC_GM = re.compile(r"(?<![A-Za-z0-9])GM[\s_-]?(\d{2,6})(?!\d)", re.IGNORECASE)
FOLDER_MIME = "application/vnd.google-apps.folder"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.metadata.readonly"


class DriveInventarioError(RuntimeError):
    pass


def validar_id(valor: str) -> str:
    if not DRIVE_ID.fullmatch(valor):
        raise ValueError("El identificador de Drive no es válido.")
    return valor


def numero_oc_candidato(nombre: str) -> str | None:
    coincidencias = {int(numero) for numero in OC_GM.findall(nombre)}
    if len(coincidencias) != 1:
        return None
    return f"GM{coincidencias.pop()}"


@dataclass(frozen=True)
class ArchivoDriveOC:
    file_id: str
    version: str
    nombre: str
    tipo_mime: str
    modificado: str | None
    ruta: str


class ClienteDrive(Protocol):
    def get(self, url: str, *, params: dict, timeout: int): ...


class GoogleDriveInventario:
    """Lectura recursiva con paginación y límites explícitos."""

    def __init__(self, cliente: ClienteDrive | None = None):
        if cliente is None:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession
            credentials, _ = google.auth.default(scopes=[DRIVE_SCOPE])
            cliente = AuthorizedSession(credentials)
        self.cliente = cliente

    def _pagina(self, carpeta_id: str, pagina: str | None) -> dict:
        params = {
            "q": f"'{validar_id(carpeta_id)}' in parents and trashed = false",
            "fields": "nextPageToken,files(id,name,mimeType,version,modifiedTime)",
            "pageSize": 1000,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
        if pagina:
            params["pageToken"] = pagina
        try:
            respuesta = self.cliente.get(
                "https://www.googleapis.com/drive/v3/files",
                params=params,
                timeout=30,
            )
            if respuesta.status_code != 200:
                raise DriveInventarioError(
                    f"Google Drive no respondió correctamente (HTTP {respuesta.status_code})."
                )
            return respuesta.json()
        except DriveInventarioError:
            raise
        except Exception as exc:
            # No filtrar datos sensibles del proveedor a logs o respuestas.
            raise DriveInventarioError("No fue posible leer Google Drive.") from exc

    def recorrer(
        self,
        raiz_id: str,
        *,
        max_carpetas: int = 3000,
        max_archivos: int = 10000,
    ) -> tuple[ArchivoDriveOC, ...]:
        validar_id(raiz_id)
        pendientes: deque[tuple[str, tuple[str, ...]]] = deque([(raiz_id, ())])
        visitadas: set[str] = set()
        archivos: list[ArchivoDriveOC] = []
        while pendientes:
            carpeta, ruta = pendientes.popleft()
            if carpeta in visitadas:
                continue
            if len(visitadas) >= max_carpetas:
                raise DriveInventarioError("Se superó el límite de carpetas; no se guardó una carga parcial.")
            visitadas.add(carpeta)
            pagina = None
            while True:
                respuesta = self._pagina(carpeta, pagina)
                for item in respuesta.get("files", ()):
                    identidad = item.get("id", "")
                    if not DRIVE_ID.fullmatch(identidad):
                        continue
                    nombre = str(item.get("name") or "")
                    mime = str(item.get("mimeType") or "")
                    if mime == FOLDER_MIME:
                        pendientes.append((identidad, (*ruta, nombre)))
                    else:
                        if len(archivos) >= max_archivos:
                            raise DriveInventarioError(
                                "Se superó el límite de archivos; no se guardó una carga parcial."
                            )
                        archivos.append(
                            ArchivoDriveOC(
                                file_id=identidad,
                                version=str(item.get("version") or item.get("modifiedTime") or "desconocida"),
                                nombre=nombre,
                                tipo_mime=mime,
                                modificado=item.get("modifiedTime"),
                                ruta=" / ".join(ruta),
                            )
                        )
                siguiente = respuesta.get("nextPageToken")
                if not siguiente:
                    break
                if siguiente == pagina:
                    raise DriveInventarioError("Paginación de Drive repetida.")
                pagina = siguiente
        return tuple(archivos)


class DocumentoDriveOC(Base):
    __tablename__ = "cartera_oc_drive_documentos"
    __table_args__ = (
        UniqueConstraint("drive_file_id", "drive_version", name="uq_cartera_oc_drive_revision"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    drive_file_id: Mapped[str] = mapped_column(String(150), nullable=False)
    drive_version: Mapped[str] = mapped_column(String(80), nullable=False)
    nombre_original: Mapped[str] = mapped_column(String(500), nullable=False)
    ruta_carpetas: Mapped[str] = mapped_column(String(1800), nullable=False, default="")
    mime_type: Mapped[str] = mapped_column(String(160), nullable=False)
    modificado_drive: Mapped[str | None] = mapped_column(String(80))
    numero_oc_candidato: Mapped[str | None] = mapped_column(String(80))
    empresa_id: Mapped[int | None] = mapped_column(
        ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=True
    )
    estado: Mapped[str] = mapped_column(String(32), nullable=False, default="SIN_ASIGNAR")
    visto_primera_vez: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    visto_ultima_vez: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


def registrar_inventario(
    session: Session, archivos: tuple[ArchivoDriveOC, ...]
) -> dict[str, int]:
    """Historial inmutable por versión; registros nuevos nunca asignan empresa."""
    nuevos = 0
    existentes = 0
    pdfs = 0
    ahora = datetime.now(timezone.utc)
    for archivo in archivos:
        if archivo.tipo_mime == "application/pdf":
            pdfs += 1
        fila = session.scalar(
            select(DocumentoDriveOC).where(
                DocumentoDriveOC.drive_file_id == archivo.file_id,
                DocumentoDriveOC.drive_version == archivo.version,
            )
        )
        if fila is not None:
            fila.visto_ultima_vez = ahora
            existentes += 1
            continue
        session.add(
            DocumentoDriveOC(
                drive_file_id=archivo.file_id,
                drive_version=archivo.version,
                nombre_original=archivo.nombre[:500],
                ruta_carpetas=archivo.ruta[:1800],
                mime_type=archivo.tipo_mime[:160],
                modificado_drive=archivo.modificado,
                numero_oc_candidato=numero_oc_candidato(archivo.nombre),
                empresa_id=None,
                estado="SIN_ASIGNAR",
                visto_ultima_vez=ahora,
            )
        )
        nuevos += 1
    session.flush()
    return {"inventariados": len(archivos), "pdfs": pdfs, "nuevos": nuevos, "existentes": existentes}


def sincronizar_desde_entorno(session: Session) -> dict[str, int]:
    """Invocación manual y exclusiva desde consola de administración."""
    raiz = os.getenv("CARTERA_OC_DRIVE_FOLDER_ID", "").strip()
    if not raiz:
        raise ValueError("Configura CARTERA_OC_DRIVE_FOLDER_ID antes de sincronizar.")
    lector = GoogleDriveInventario()
    archivos = lector.recorrer(raiz)
    return registrar_inventario(session, archivos)
