"""Consulta de aptitud para aplicar correcciones; no ejecuta movimientos contables."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.auth.dependencias import Acceso, requiere
from app.core.session import obtener_session
from .preflight_aplicacion import evaluar

router=APIRouter(prefix="/wallets/periodos",tags=["wallets"])

def _empresa(empresa_id:int)->int:
    return empresa_id

ver=requiere("conciliacion.ver",empresa_de=_empresa)

@router.get("/{periodo_id}/expedientes-correccion/{expediente_id}/preflight")
def consultar_preflight(empresa_id:int,periodo_id:int,expediente_id:int,
                        _acceso:Acceso=Depends(ver),
                        session:Session=Depends(obtener_session))->dict:
    try:
        return evaluar(session,empresa_id=empresa_id,periodo_id=periodo_id,
                       expediente_id=expediente_id)
    except LookupError as exc:
        raise HTTPException(status_code=404,detail=str(exc)) from exc
