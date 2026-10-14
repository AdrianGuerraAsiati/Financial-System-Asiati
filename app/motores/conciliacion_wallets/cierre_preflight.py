"""Diagnóstico previo de cierre de Wallets; nunca autoriza ni ejecuta un cierre."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.hallazgos.model import Hallazgo
from app.core.periodos import Periodo
from .historial import WalletEjecucionHistorial


def diagnostico_cierre_wallets(session: Session, *, empresa_id: int, periodo_id: int) -> dict:
    periodo = session.get(Periodo, periodo_id)
    if periodo is None or periodo.empresa_id != empresa_id:
        raise ValueError("El período no pertenece a la empresa indicada.")

    registros = list(session.scalars(
        select(WalletEjecucionHistorial)
        .where(WalletEjecucionHistorial.empresa_id == empresa_id,
               WalletEjecucionHistorial.periodo_id == periodo_id)
        .order_by(WalletEjecucionHistorial.id.desc())
    ))
    # Una ejecución previa correcta no borra un C0 bloqueado posterior.
    ultimos = {}
    for registro in registros:
        identidad = (registro.identidad_wallet or "").strip().lower()
        llave = (registro.tipo_wallet, identidad)
        if llave not in ultimos:
            ultimos[llave] = registro

    pendientes = list(session.scalars(
        select(Hallazgo).where(
            Hallazgo.periodo_id == periodo_id,
            Hallazgo.motor_slug == "conciliacion_wallets",
            Hallazgo.resuelto.is_(False),
        )
    ))
    bloqueados = [
        {"tipo_wallet": tipo, "identidad_wallet": identidad or None,
         "ejecucion_id": registro.id}
        for (tipo, identidad), registro in ultimos.items()
        if registro.bloqueado or not (registro.resultado.get("c0") or {}).get("cuadra")
    ]
    razones = []
    if not ultimos:
        razones.append("No existen ejecuciones históricas de Wallets para el período.")
    if bloqueados:
        razones.append("Existen últimas ejecuciones con C0 bloqueado o no conciliado.")
    if pendientes:
        razones.append("Existen hallazgos de Wallets sin resolver, de cualquier gravedad.")
    # El alcance de wallets esperadas, margen operativo y firma funcional
    # no están definidos como contratos ejecutables; se bloquea el cierre.
    razones.append("Faltan reglas de corte, cobertura de wallets y aprobación financiera formalizadas.")
    return {
        "empresa_id": empresa_id,
        "periodo_id": periodo_id,
        "periodo_cerrado": periodo.cerrado,
        "ejecuciones_ultimas": len(ultimos),
        "ejecuciones_bloqueadas": bloqueados,
        "hallazgos_pendientes": len(pendientes),
        "criticos_abiertos": sum(1 for h in pendientes if h.critico),
        "puede_cerrar": False,
        "razones": razones,
    }
