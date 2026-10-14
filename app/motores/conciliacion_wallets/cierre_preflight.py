"""Diagnóstico previo de cierre de Wallets; nunca autoriza ni ejecuta un cierre."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.hallazgos.model import Hallazgo
from app.core.periodos import Periodo
from .historial import WalletEjecucionHistorial
from .esperadas import claves_esperadas


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

    esperadas = claves_esperadas(session, empresa_id=empresa_id, periodo_id=periodo_id)
    faltantes = [
        {"tipo_wallet": tipo, "identidad_wallet": identidad or None}
        for tipo, identidad in sorted(esperadas - set(ultimos))
    ]

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
        if (tipo, identidad) in esperadas and (registro.bloqueado or not (registro.resultado.get("c0") or {}).get("cuadra"))
    ]
    razones = []
    if not esperadas:
        razones.append("El catálogo de wallets esperadas no está definido para este período.")
    if faltantes:
        razones.append("Faltan conciliaciones de wallets obligatorias; las excepciones no habilitan el cierre.")
    if not ultimos:
        razones.append("No existen ejecuciones históricas de Wallets para el período.")
    if bloqueados:
        razones.append("Existen últimas ejecuciones con C0 bloqueado o no conciliado.")
    if pendientes:
        razones.append("Existen hallazgos de Wallets sin resolver, de cualquier gravedad.")
    # La cobertura se diagnostica; catálogo, corte y firma siguen pendientes de aprobación.
    razones.append("Faltan validación formal del catálogo, reglas de corte y aprobación financiera.")
    return {
        "empresa_id": empresa_id,
        "periodo_id": periodo_id,
        "periodo_cerrado": periodo.cerrado,
        "ejecuciones_ultimas": len(ultimos),
        "wallets_esperadas": len(esperadas),
        "wallets_faltantes": faltantes,
        "wallets_adicionales": [
            {"tipo_wallet": tipo, "identidad_wallet": identidad or None}
            for tipo, identidad in sorted(set(ultimos) - esperadas)
        ],
        "ejecuciones_bloqueadas": bloqueados,
        "hallazgos_pendientes": len(pendientes),
        "criticos_abiertos": sum(1 for h in pendientes if h.critico),
        "puede_cerrar": False,
        "razones": razones,
    }
