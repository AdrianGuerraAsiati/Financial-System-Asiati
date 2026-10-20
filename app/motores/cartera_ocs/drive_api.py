"""Consulta protegida del inventario documental, no de cartera real."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
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
    total = session.scalar(select(func.count()).select_from(DocumentoDriveOC)) or 0
    registros = session.scalars(
        select(DocumentoDriveOC).order_by(DocumentoDriveOC.id.desc())
        .offset(offset).limit(limit)
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
