"""Edición auditada de campos administrativos y vencimiento de facturas."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auditoria.service import registrar_auditoria
from app.core.auth.dependencias import Acceso, requiere
from app.core.session import obtener_session
from app.motores.tesoreria.api import _factura, _texto, _dimension, _json

router = APIRouter(prefix="/tesoreria", tags=["tesoreria"])


class CambiosFactura(BaseModel):
    fecha_vencimiento: date | None = None
    descripcion: str | None = None
    ciudad: str | None = None
    unidad_negocio: str | None = None
    categoria: str | None = None
    fijo_variable: str | None = None
    cuenta_pago: str | None = None
    documento_contable: str | None = None


@router.patch("/facturas/{factura_id}")
def actualizar(
    factura_id: int, cambios: CambiosFactura,
    acceso: Acceso = Depends(requiere("tesoreria.facturas.gestionar")),
    session: Session = Depends(obtener_session),
) -> dict:
    factura = _factura(session, acceso, factura_id)
    datos = cambios.model_dump(exclude_unset=True)
    if not datos:
        raise HTTPException(422, "No hay campos por cambiar.")
    for campo in ("ciudad", "unidad_negocio", "categoria", "fijo_variable",
                  "cuenta_pago", "documento_contable", "descripcion"):
        if campo not in datos:
            continue
        texto = _texto(datos[campo], 1000 if campo == "descripcion" else
                       200 if campo == "cuenta_pago" else 100 if campo == "ciudad" else 120,
                       obligatorio=campo == "descripcion")
        datos[campo] = _dimension(session, campo, texto) if campo in (
            "unidad_negocio", "categoria", "fijo_variable") else texto
    antes = {campo: str(getattr(factura, campo)) if isinstance(
        getattr(factura, campo), date) else getattr(factura, campo) for campo in datos}
    for campo, valor in datos.items():
        setattr(factura, campo, valor)
    despues = {k: str(v) if isinstance(v, date) else v for k, v in datos.items()}
    registrar_auditoria(session, usuario_id=acceso.usuario.id, empresa_id=factura.empresa_id,
                        ip=acceso.ip, accion="tesoreria.factura.editar",
                        entidad="factura_compra", entidad_id=factura.id, antes=antes, despues=despues)
    session.commit()
    return _json(session, factura, detalle=True)
