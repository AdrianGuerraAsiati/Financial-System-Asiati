"""Bandeja de *ingresos reportados*, sin verificación bancaria ni aplicación CxC.

Todos los importes son datos informados por un operador y permanecen bajo el
estado PENDIENTE_VERIFICACION. Ni siquiera el superadministrador puede
declararlos conciliados mediante esta API.
"""
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auditoria.service import registrar_auditoria
from app.core.auth.dependencias import Acceso, requiere
from app.core.dimensiones.service import normalizar
from app.core.empresas import Empresa
from app.core.session import obtener_session
from app.motores.recaudos.model import IngresoReportado

router = APIRouter(prefix="/recaudos", tags=["recaudos"])
Moneda = Literal["COP", "USD", "CLP"]
ESTADO = "PENDIENTE_VERIFICACION"


class RegistroManual(BaseModel):
    model_config = ConfigDict(extra="forbid")
    empresa_id: int = Field(gt=0)
    fecha_reportada: date
    monto: Decimal
    moneda: Moneda = "COP"
    cuenta_receptora: str = Field(min_length=1, max_length=200)
    referencia_origen: str = Field(min_length=1, max_length=120)
    pagador_reportado: str | None = Field(default=None, max_length=255)
    descripcion: str | None = Field(default=None, max_length=1000)


def _empresa_visible(session: Session, acceso: Acceso, empresa_id: int) -> None:
    if ((acceso.empresas_visibles is not None and empresa_id not in acceso.empresas_visibles)
            or session.get(Empresa, empresa_id) is None):
        raise HTTPException(status_code=404, detail="Empresa no encontrada.")


def _texto(valor: str | None, maximo: int, obligatorio: bool = False) -> str | None:
    texto = " ".join((valor or "").split())
    if (obligatorio and not texto) or len(texto) > maximo:
        raise HTTPException(status_code=422, detail=f"Dato obligatorio o demasiado largo (máximo {maximo}).")
    return texto or None


def _importe(valor: Decimal) -> Decimal:
    if (not valor.is_finite() or valor <= 0
            or valor.as_tuple().exponent < -2
            or valor > Decimal("9999999999999999.99")):
        raise HTTPException(status_code=422, detail="Monto positivo, finito y máximo dos decimales.")
    return valor.quantize(Decimal("0.01"))


def _json(x: IngresoReportado) -> dict:
    return {
        "id": x.id,
        "empresa_id": x.empresa_id,
        "fecha_reportada": x.fecha_reportada,
        "monto_reportado": format(x.monto, ".2f"),
        "moneda": x.moneda,
        "cuenta_receptora": x.cuenta_receptora,
        "referencia_origen": x.referencia_origen,
        "pagador_reportado": x.pagador_reportado,
        "descripcion": x.descripcion,
        "origen": x.origen,
        "estado": x.estado,
        "aplicado_a_cartera": False,
        "verificado_con_banco": False,
        "registrado_por": x.registrado_por,
        "registrado_at": x.registrado_at,
    }


@router.post("/ingresos", status_code=201)
def crear_ingreso(
    datos: RegistroManual,
    acceso: Acceso = Depends(requiere("recaudos.registrar")),
    session: Session = Depends(obtener_session),
) -> dict:
    _empresa_visible(session, acceso, datos.empresa_id)
    cuenta = _texto(datos.cuenta_receptora, 200, obligatorio=True)
    referencia = _texto(datos.referencia_origen, 120, obligatorio=True)
    pagador = _texto(datos.pagador_reportado, 255)
    descripcion = _texto(datos.descripcion, 1000)
    monto = _importe(datos.monto)
    clave_cuenta = normalizar(cuenta)
    clave_referencia = normalizar(referencia)
    if session.scalar(select(IngresoReportado.id).where(
        IngresoReportado.empresa_id == datos.empresa_id,
        IngresoReportado.cuenta_clave == clave_cuenta,
        IngresoReportado.referencia_clave == clave_referencia,
    )):
        raise HTTPException(409, "La referencia ya está registrada para esta cuenta y empresa.")

    ingreso = IngresoReportado(
        empresa_id=datos.empresa_id,
        fecha_reportada=datos.fecha_reportada,
        monto=monto,
        moneda=datos.moneda,
        cuenta_receptora=cuenta,
        cuenta_clave=clave_cuenta,
        referencia_origen=referencia,
        referencia_clave=clave_referencia,
        pagador_reportado=pagador,
        descripcion=descripcion,
        origen="MANUAL",
        estado=ESTADO,
        registrado_por=acceso.usuario.id,
    )
    try:
        session.add(ingreso)
        session.flush()
        registrar_auditoria(
            session, usuario_id=acceso.usuario.id, empresa_id=ingreso.empresa_id,
            ip=acceso.ip, accion="recaudos.ingreso_reportado.crear",
            entidad="ingreso_reportado", entidad_id=ingreso.id,
            despues={"fecha_reportada": datos.fecha_reportada.isoformat(),
                     "monto_reportado": format(monto, ".2f"),
                     "moneda": datos.moneda, "origen": "MANUAL",
                     "estado": ESTADO, "referencia_origen": referencia},
        )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "La referencia ya está registrada para esta cuenta y empresa.") from exc
    except Exception:
        session.rollback()
        raise
    return _json(ingreso)


@router.get("/ingresos")
def listar_ingresos(
    empresa_id: int = Query(..., gt=0),
    moneda: Moneda | None = Query(None),
    buscar: str = Query("", max_length=120),
    desde_fecha: date | None = Query(None),
    hasta_fecha: date | None = Query(None),
    limite: int = Query(25, ge=1, le=100),
    desde: int = Query(0, ge=0),
    acceso: Acceso = Depends(requiere("recaudos.ver")),
    session: Session = Depends(obtener_session),
) -> dict:
    _empresa_visible(session, acceso, empresa_id)
    if desde_fecha and hasta_fecha and desde_fecha > hasta_fecha:
        raise HTTPException(422, "La fecha inicial debe ser anterior o igual a la final.")
    condiciones = [IngresoReportado.empresa_id == empresa_id]
    if moneda:
        condiciones.append(IngresoReportado.moneda == moneda)
    if desde_fecha:
        condiciones.append(IngresoReportado.fecha_reportada >= desde_fecha)
    if hasta_fecha:
        condiciones.append(IngresoReportado.fecha_reportada <= hasta_fecha)
    if buscar.strip():
        texto = buscar.strip().replace("!", "!!").replace("%", "!%").replace("_", "!_")
        patron = f"%{texto}%"
        condiciones.append(or_(
            IngresoReportado.referencia_origen.ilike(patron, escape="!"),
            IngresoReportado.pagador_reportado.ilike(patron, escape="!"),
            IngresoReportado.cuenta_receptora.ilike(patron, escape="!"),
        ))
    total = session.scalar(select(func.count()).select_from(IngresoReportado).where(*condiciones)) or 0
    items = session.scalars(
        select(IngresoReportado).where(*condiciones)
        .order_by(IngresoReportado.fecha_reportada.desc(), IngresoReportado.id.desc())
        .offset(desde).limit(limite)
    )
    return {
        "items": [_json(x) for x in items],
        "total": total, "desde": desde, "limite": limite,
        "nota": "Movimientos reportados por el usuario; no verificados ni aplicados a Cartera.",
    }


@router.get("/ingresos/{ingreso_id}")
def detalle_ingreso(
    ingreso_id: int,
    acceso: Acceso = Depends(requiere("recaudos.ver")),
    session: Session = Depends(obtener_session),
) -> dict:
    ingreso = session.get(IngresoReportado, ingreso_id)
    if ingreso is None:
        raise HTTPException(404, "Ingreso reportado no encontrado.")
    _empresa_visible(session, acceso, ingreso.empresa_id)
    return _json(ingreso)
