"""Consulta del inventario documental. Referencias OC propuestas, no cartera validada."""
import re
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.auth.dependencias import Acceso, requiere
from app.core.permisos import Alcance
from app.core.session import obtener_session
from app.motores.cartera_ocs.drive_index import DocumentoDriveOC, validar_id

router = APIRouter(prefix="/cartera/ocs/drive", tags=["cartera-drive"])


@router.get("/inventario")
def consultar_inventario_drive(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    buscar: str = Query("", max_length=100),
    _acceso: Acceso = Depends(requiere("cartera.ver")),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    # El Drive incluye O.C. de varias sociedades. Mientras Juanfe no valide
    # la asignación jurídica, NO exponer nombres ni archivos por empresa.
    if _acceso.alcance is not Alcance.TODAS:
        raise HTTPException(
            status_code=403,
            detail="El inventario sin asignación jurídica solo está disponible para administración global.",
        )
    termino = buscar.strip()
    filtros = []
    if termino:
        # Tratar comodines ingresados como texto literal, no como patrones SQL.
        literal = termino.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        patron = f"%{literal}%"
        filtros.append(or_(
            DocumentoDriveOC.nombre_original.ilike(patron, escape="\\"),
            DocumentoDriveOC.ruta_carpetas.ilike(patron, escape="\\"),
            DocumentoDriveOC.numero_oc_candidato.ilike(patron, escape="\\"),
        ))
    total = session.scalar(
        select(func.count()).select_from(DocumentoDriveOC).where(*filtros)
    ) or 0
    registros = session.scalars(
        select(DocumentoDriveOC).where(*filtros)
        .order_by(DocumentoDriveOC.id.desc()).offset(offset).limit(limit)
    ).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": item.id,
                "nombre": item.nombre_original,
                "ruta": item.ruta_carpetas,
                "tipo_mime": item.mime_type,
                "numero_oc_candidato": item.numero_oc_candidato,
                "revision": item.drive_version,
                "empresa_id": item.empresa_id,
                "estado": item.estado,
                "ultima_modificacion": item.modificado_drive,
                "url_origen": (
                    "https://drive.google.com/file/d/"
                    + validar_id(item.drive_file_id)
                    + "/view"
                ),
            }
            for item in registros
        ],
        "nota": (
            "Inventario documental de solo lectura; no representa saldo de cartera. "
            "Los números GM tomados del nombre son candidatos, no identificadores validados. "
            "Actualizar la página no ejecuta sincronización de Drive."
        ),
    }


def _acceso_global_cartera(
    acceso: Acceso = Depends(requiere("cartera.ver")),
) -> Acceso:
    """Nombres y enlaces de O.C. sin atribución jurídica solo para alcance global."""
    if acceso.alcance is not Alcance.TODAS:
        raise HTTPException(
            status_code=403,
            detail="Las O.C. sin empresa validada requieren permiso global de Cartera.",
        )
    return acceso


def _documentos_actuales(session: Session) -> list[DocumentoDriveOC]:
    """Una revisión visible por archivo físico; conserva su histórico en la tabla."""
    ultimos = (
        select(func.max(DocumentoDriveOC.id))
        .group_by(DocumentoDriveOC.drive_file_id)
    )
    return list(
        session.scalars(
            select(DocumentoDriveOC)
            .where(DocumentoDriveOC.id.in_(ultimos))
            .order_by(DocumentoDriveOC.id.desc())
        )
    )


def _fecha_drive_utc(valor: object) -> datetime | None:
    """Interpreta la marca temporal del índice; las fechas ausentes van al final."""
    if not isinstance(valor, str) or not valor.strip():
        return None
    try:
        fecha = datetime.fromisoformat(valor.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone(timezone.utc)


def _ordenar_ordenes_documentales(
    items: list[dict[str, object]],
    orden: Literal["fecha_desc", "fecha_asc", "oc_asc", "oc_desc"],
) -> list[dict[str, object]]:
    """Ordena todas las OC filtradas ANTES de paginar; empates por OC A–Z.

    La fecha corresponde al documento Drive vigente más reciente dentro de
    cada grupo candidato, no a la fecha jurídica de la orden.
    """
    def clave_gm(grupo: dict[str, object]) -> tuple[object, ...]:
        numero = str(grupo["numero_oc"]).strip().upper()
        encontrado = re.fullmatch(r"GM(\d+)", numero)
        if encontrado:
            return (0, int(encontrado.group(1)), numero)
        return (1, numero)

    por_oc = sorted(items, key=clave_gm)
    if orden == "oc_asc":
        return por_oc
    if orden == "oc_desc":
        return list(reversed(por_oc))
    con_fecha: list[tuple[dict[str, object], datetime]] = []
    sin_fecha: list[dict[str, object]] = []
    for grupo in por_oc:
        fecha = _fecha_drive_utc(grupo["ultima_modificacion"])
        if fecha is None:
            sin_fecha.append(grupo)
        else:
            con_fecha.append((grupo, fecha))
    # sort estable: para igual fecha conserva el orden alfabético por OC.
    con_fecha.sort(key=lambda par: par[1], reverse=orden == "fecha_desc")
    return [grupo for grupo, _ in con_fecha] + sin_fecha


@router.get("/ordenes")
def listar_ordenes_documentales(
    buscar: str = Query("", max_length=50),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    orden: Literal["fecha_desc", "fecha_asc", "oc_asc", "oc_desc"] = Query("oc_asc"),
    _acceso: Acceso = Depends(_acceso_global_cartera),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    """Lista agrupaciones candidatas GM con soporte, no O.C. jurídicas confirmadas."""
    actuales = _documentos_actuales(session)
    grupos: dict[str, dict[str, object]] = {}
    sin_oc = 0
    for documento in actuales:
        numero = documento.numero_oc_candidato
        if not numero:
            sin_oc += 1
            continue
        grupo = grupos.setdefault(numero, {
            "numero_oc": numero,
            "soportes": 0,
            "ultima_modificacion": None,
            "estado": "SIN_VALIDAR",
        })
        grupo["soportes"] += 1
        fecha = documento.modificado_drive
        if fecha and (grupo["ultima_modificacion"] is None or fecha > grupo["ultima_modificacion"]):
            grupo["ultima_modificacion"] = fecha

    patron = buscar.strip().upper()
    items = [
        grupo for numero, grupo in grupos.items()
        if not patron or patron in numero
    ]
    items = _ordenar_ordenes_documentales(items, orden)
    # La paginación se aplica a órdenes, nunca a líneas o versiones sueltas.
    return {
        "total": len(items),
        "total_ocs_detectadas": len(grupos),
        "archivos_sin_oc": sin_oc,
        "archivos_vigentes": len(actuales),
        "limit": limit,
        "offset": offset,
        "orden": orden,
        "items": items[offset:offset + limit],
        "nota": (
            "Referencias GM detectadas únicamente por nombre de archivo. "
            "Sin asignación jurídica, sin cálculo de cartera y sin acceso a PDFs desde el servidor. "
            "Los enlaces de Google Drive requieren permisos del usuario en Google."
        ),
    }


@router.get("/ordenes/{numero_oc}/soportes")
def soportes_de_orden_documental(
    numero_oc: str,
    _acceso: Acceso = Depends(_acceso_global_cartera),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    """Devuelve solo la revisión actual de cada soporte identificado por GM."""
    limpio = numero_oc.strip().upper()
    if not re.fullmatch(r"GM\d{1,6}", limpio):
        raise HTTPException(status_code=422, detail="Número de O.C. no válido.")
    normalizado = f"GM{int(limpio[2:])}"
    archivos = [
        documento for documento in _documentos_actuales(session)
        if documento.numero_oc_candidato == normalizado
    ]
    if not archivos:
        raise HTTPException(status_code=404, detail="No hay soportes indexados para esa referencia.")
    return {
        "numero_oc": normalizado,
        "estado": "SIN_VALIDAR",
        "total": len(archivos),
        "items": [
            {
                "id": documento.id,
                "nombre": documento.nombre_original,
                "ruta": documento.ruta_carpetas,
                "tipo_mime": documento.mime_type,
                "revision": documento.drive_version,
                "ultima_modificacion": documento.modificado_drive,
                "url_origen": (
                    "https://drive.google.com/file/d/"
                    + validar_id(documento.drive_file_id)
                    + "/view"
                ),
            }
            for documento in archivos
        ],
        "nota": "Relación sugerida por nombre de archivo; no confirma propiedad, empresa ni saldo.",
    }
