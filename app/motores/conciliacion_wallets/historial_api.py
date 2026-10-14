"""Consulta histórica con alcance financiero por empresa."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth.dependencias import Acceso, requiere
from app.core.session import obtener_session
from .historial import listar_historial
from .cierre_preflight import diagnostico_cierre_wallets

router = APIRouter(prefix="/wallets", tags=["wallets"])

def _empresa(empresa_id: int) -> int:
    return empresa_id

ver = requiere("conciliacion.ver", empresa_de=_empresa)


@router.get("/ejecuciones")
def consultar_ejecuciones(
    empresa_id: int, periodo_id: int, tipo_wallet: str,
    identidad_wallet: str | None = None,
    _acceso: Acceso = Depends(ver),
    session: Session = Depends(obtener_session),
) -> list[dict]:
    if tipo_wallet not in ("wiilog", "tienda", "pagos"):
        raise HTTPException(status_code=422, detail="Tipo de wallet no válido.")
    try:
        registros = listar_historial(session, empresa_id=empresa_id, periodo_id=periodo_id,
                                   tipo_wallet=tipo_wallet, identidad_wallet=identidad_wallet)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [
        {"id": r.id, "creado_at": r.creado_at, "bloqueado": r.bloqueado,
         "carga_wallet_id": r.carga_wallet_id, "carga_ordenes_id": r.carga_ordenes_id,
         "resultado": r.resultado}
        for r in registros
    ]


@router.get("/periodos/{periodo_id}/diagnostico-cierre")
def diagnosticar_cierre(
    periodo_id: int, empresa_id: int,
    _acceso: Acceso = Depends(ver),
    session: Session = Depends(obtener_session),
) -> dict:
    """Solo lectura. No aplica cierre ni modifica el período."""
    try:
        return diagnostico_cierre_wallets(session, empresa_id=empresa_id, periodo_id=periodo_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
