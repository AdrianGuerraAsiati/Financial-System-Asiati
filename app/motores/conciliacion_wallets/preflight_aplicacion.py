"""Preflight de aplicación financiera: modo seguro, sin escribir asientos ni saldos."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.periodos import Periodo
from app.core.cargas import Carga
from .expedientes_correccion import ExpedienteCorreccion
from .ejecucion_reapertura import EjecucionReapertura
from .historial import WalletEjecucionHistorial


def evaluar(session: Session, *, empresa_id: int, periodo_id: int,
            expediente_id: int) -> dict:
    periodo = session.scalar(select(Periodo).where(
        Periodo.id == periodo_id, Periodo.empresa_id == empresa_id))
    if periodo is None:
        raise LookupError("Período no encontrado para la empresa.")
    expediente = session.scalar(select(ExpedienteCorreccion).where(
        ExpedienteCorreccion.id == expediente_id,
        ExpedienteCorreccion.empresa_id == empresa_id,
        ExpedienteCorreccion.periodo_id == periodo_id))
    if expediente is None:
        raise LookupError("Expediente no encontrado.")
    bloqueos = []
    if periodo.cerrado:
        bloqueos.append("PERIODO_CERRADO")
    if expediente.decision != "AUTORIZAR_EJECUCION":
        bloqueos.append("SIN_AUTORIZACION_FINANCIERA")
    if expediente.decidido_por is None or expediente.preparado_por == expediente.decidido_por:
        bloqueos.append("SIN_SEGREGACION_VALIDA")
    if session.scalar(select(EjecucionReapertura.id).where(
        EjecucionReapertura.id == expediente.ejecucion_id,
        EjecucionReapertura.empresa_id == empresa_id,
        EjecucionReapertura.periodo_id == periodo_id)) is None:
        bloqueos.append("SIN_REAPERTURA_VERIFICADA")
    carga = session.scalar(select(Carga).where(
        Carga.id == expediente.carga_id, Carga.empresa_id == empresa_id,
        Carga.periodo_id == periodo_id))
    if carga is None:
        bloqueos.append("SIN_CARGA_ORIGINAL")
    historial = session.scalar(select(WalletEjecucionHistorial.id).where(
        WalletEjecucionHistorial.empresa_id == empresa_id,
        WalletEjecucionHistorial.periodo_id == periodo_id,
        WalletEjecucionHistorial.carga_wallet_id == expediente.carga_id))
    if historial is None:
        bloqueos.append("SIN_HISTORIAL_CONCILIACION")
    # El JSON de historial no define una referencia canónica estable por movimiento.
    # Nunca inferir un importe desde texto, evidencia declarada o datos agregados.
    bloqueos.append("MOVIMIENTO_E_IMPORTE_ORIGINAL_NO_VERIFICADOS")
    bloqueos.append("MOTOR_APLICACION_CONTABLE_NO_IMPLEMENTADO")
    return {
        "empresa_id": empresa_id, "periodo_id": periodo_id,
        "expediente_id": expediente.id, "carga_id": expediente.carga_id,
        "movimiento_ref": expediente.movimiento_ref,
        "valor_declarado_anterior": str(expediente.valor_anterior),
        "valor_propuesto": str(expediente.valor_propuesto),
        "verificacion_movimiento": False,
        "puede_aplicar": False, "aplicada": False,
        "bloqueos": bloqueos,
    }
