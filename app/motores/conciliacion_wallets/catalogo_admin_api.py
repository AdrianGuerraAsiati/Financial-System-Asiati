"""Administración autorizada del catálogo, separada de cierre financiero."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth.dependencias import Acceso, requiere
from app.core.session import obtener_session
from .catalogo_admin import CatalogoCongeladoError, catalogo, agregar, quitar, aprobar

router = APIRouter(prefix="/wallets/periodos", tags=["wallets"])

def _empresa(empresa_id: int) -> int:
    return empresa_id

ver = requiere("conciliacion.ver", empresa_de=_empresa)
preparar = requiere("conciliacion.ejecutar", empresa_de=_empresa)
autorizar = requiere("periodos.cerrar", empresa_de=_empresa)


class NuevaWallet(BaseModel):
    tipo_wallet: str
    identidad_wallet: str | None = None
    vigente_desde: date | None = None
    vigente_hasta: date | None = None


class Motivo(BaseModel):
    motivo: str = Field(min_length=1, max_length=2000)


def _hacer(session: Session, fn):
    try:
        resultado = fn()
        session.commit()
        return resultado
    except LookupError as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (CatalogoCongeladoError, IntegrityError) as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Catálogo congelado, duplicado o inconsistente.") from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        session.rollback()
        raise


@router.get("/{periodo_id}/wallets-esperadas")
def consultar(empresa_id: int, periodo_id: int, _acceso: Acceso = Depends(ver),
              session: Session = Depends(obtener_session)) -> dict:
    try:
        return catalogo(session, empresa_id=empresa_id, periodo_id=periodo_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{periodo_id}/wallets-esperadas", status_code=201)
def registrar(empresa_id: int, periodo_id: int, datos: NuevaWallet,
             acceso: Acceso = Depends(preparar),
             session: Session = Depends(obtener_session)) -> dict:
    item = _hacer(session, lambda: agregar(
        session, empresa_id=empresa_id, periodo_id=periodo_id,
        usuario_id=acceso.usuario.id, tipo_wallet=datos.tipo_wallet,
        identidad_wallet=datos.identidad_wallet, ip=acceso.ip,
        vigente_desde=datos.vigente_desde, vigente_hasta=datos.vigente_hasta))
    return {"id": item.id, "tipo_wallet": item.tipo_wallet, "identidad_wallet": item.identidad_wallet,
            "vigente_desde": item.vigente_desde, "vigente_hasta": item.vigente_hasta}


@router.delete("/{periodo_id}/wallets-esperadas/{item_id}", status_code=204)
def retirar(empresa_id: int, periodo_id: int, item_id: int, datos: Motivo,
            acceso: Acceso = Depends(preparar), session: Session = Depends(obtener_session)) -> None:
    _hacer(session, lambda: quitar(
        session, empresa_id=empresa_id, periodo_id=periodo_id, item_id=item_id,
        usuario_id=acceso.usuario.id, motivo=datos.motivo, ip=acceso.ip))


@router.post("/{periodo_id}/wallets-esperadas/aprobar", status_code=201)
def aprobar_catalogo(empresa_id: int, periodo_id: int, datos: Motivo,
                     acceso: Acceso = Depends(autorizar),
                     session: Session = Depends(obtener_session)) -> dict:
    resultado = _hacer(session, lambda: aprobar(
        session, empresa_id=empresa_id, periodo_id=periodo_id,
        usuario_id=acceso.usuario.id, motivo=datos.motivo, ip=acceso.ip))
    return {"id": resultado.id, "aprobado": True}
