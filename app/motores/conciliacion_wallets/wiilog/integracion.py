from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cargas import calcular_hash_contenido, registrar_carga
from app.core.hallazgos import Hallazgo, registrar_hallazgo_motor
from app.core.periodos import Periodo
from app.core.periodos.errors import PeriodoCerradoError

from .motor import ResultadoWiilog, conciliar_wallet_wiilog


MOTOR_SLUG = "conciliacion_wallets"
PARAMS_PATH = (
    Path(__file__).resolve().parents[4]
    / "docs"
    / "motores"
    / "conciliacion_wallets"
    / "parametros_wallet_wiilog.json"
)


@dataclass(frozen=True)
class EjecucionWiilog:
    carga_ordenes_id: int
    carga_wallet_id: int
    bloqueado: bool
    hallazgos_creados: int
    resumen: dict[str, Any]


def cargar_parametros_wiilog() -> dict[str, Any]:
    return json.loads(PARAMS_PATH.read_text(encoding="utf-8"))


def _leer_excel(contenido: bytes, nombre: str) -> pd.DataFrame:
    if not contenido:
        raise ValueError(f"El archivo de {nombre} no puede estar vacío.")
    try:
        frame = pd.read_excel(io.BytesIO(contenido))
    except Exception as exc:
        raise ValueError(
            f"No se pudo leer el archivo de {nombre}. "
            "Confirma que sea un Excel válido exportado desde Dropi."
        ) from exc
    if frame.empty:
        raise ValueError(f"El archivo de {nombre} no puede estar vacío.")
    return frame


def _periodo_abierto(
    session: Session,
    *,
    empresa_id: int,
    periodo_id: int,
) -> Periodo:
    periodo = session.get(Periodo, periodo_id)
    if periodo is None or periodo.empresa_id != empresa_id:
        raise ValueError("El período no pertenece a la empresa indicada.")
    if periodo.cerrado:
        raise PeriodoCerradoError(
            "El período está cerrado. Reábrelo antes de ejecutar la conciliación."
        )
    return periodo


def _registrar(
    session: Session,
    *,
    periodo_id: int,
    codigo: str,
    descripcion: str,
    evidencia: dict[str, Any],
    critico: bool,
    gravedad: str,
) -> Hallazgo:
    # La gravedad va en la evidencia para la bandeja (PANTALLA_WALLETS.md §2.2); no cambia qué es hallazgo.
    evidencia = {"wallet": "WIILOG", "gravedad": gravedad, **evidencia}
    return registrar_hallazgo_motor(
        session,
        periodo_id=periodo_id,
        motor_slug=MOTOR_SLUG,
        codigo_regla=codigo,
        descripcion=descripcion,
        evidencia=evidencia,
        critico=critico,
    )


def _valor_texto(valor: object) -> str | None:
    if valor is None or pd.isna(valor):
        return None
    return str(valor)


def _persistir_chequeos(
    session: Session,
    *,
    periodo_id: int,
    resultado: ResultadoWiilog,
) -> int:
    creados = 0
    for chequeo in resultado.chequeos:
        if chequeo.estado == "EN_ORDEN":
            continue
        _registrar(
            session,
            periodo_id=periodo_id,
            codigo=f"WIILOG_{chequeo.codigo}",
            descripcion=chequeo.mensaje,
            evidencia={
                "estado": chequeo.estado,
                "detalle": chequeo.detalle,
            },
            critico=chequeo.estado == "BLOQUEADO",
            gravedad="CRITICO" if chequeo.estado == "BLOQUEADO" else "INFORMATIVO",
        )
        creados += 1
    return creados


def _persistir_movimientos(
    session: Session,
    *,
    periodo_id: int,
    resultado: ResultadoWiilog,
) -> int:
    if resultado.movimientos is None:
        return 0

    creados = 0
    revisar = resultado.movimientos[
        resultado.movimientos["estado_categoria"] != "AUTO"
    ]
    for fila in revisar.itertuples(index=False):
        _registrar(
            session,
            periodo_id=periodo_id,
            codigo=f"WIILOG_MOVIMIENTO_{fila.estado_categoria}",
            descripcion=(
                "El movimiento requiere revisión y explicación antes del cierre."
            ),
            evidencia={
                "mov_id": int(fila.mov_id),
                "fecha": str(fila.fecha),
                "concepto": _valor_texto(fila.concepto),
                "flujo": _valor_texto(fila.flujo),
                "categoria": _valor_texto(fila.categoria),
                "monto_c": int(fila.monto_c),
                "tercero": _valor_texto(fila.tercero),
                "requiere_observacion": bool(fila.requiere_observacion),
            },
            critico=False,
            gravedad="REVISAR",
        )
        creados += 1
    return creados


def _persistir_ff(
    session: Session,
    *,
    periodo_id: int,
    resultado: ResultadoWiilog,
) -> int:
    if resultado.ff is None:
        return 0

    creados = 0
    hallazgos = resultado.ff[resultado.ff["severidad"] != "informativo"]
    for orden_id, fila in hallazgos.iterrows():
        estado = str(fila["estado_ff"])
        _registrar(
            session,
            periodo_id=periodo_id,
            codigo=f"WIILOG_FF_{estado}",
            descripcion=f"Fulfillment de la orden {orden_id}: {estado}.",
            evidencia={
                "orden_id": str(orden_id),
                "estado": estado,
                "bodega": _valor_texto(fila.get("bodega")),
                "guia": _valor_texto(fila.get("guia")),
                "monto_en_juego_c": int(fila["monto_en_juego_c"]),
                "tarifa_c": int(fila["tarifa_c"]),
                "ff_neto_c": int(fila["ff_neto_c"]),
                "ff_movimientos": _valor_texto(fila.get("ff_movimientos")),
            },
            critico=str(fila["severidad"]) == "critico",
            gravedad=str(fila["severidad"]).upper(),
        )
        creados += 1
    return creados


def _persistir_flete(
    session: Session,
    *,
    periodo_id: int,
    resultado: ResultadoWiilog,
) -> int:
    if resultado.flete is None:
        return 0

    creados = 0
    hallazgos = resultado.flete[
        resultado.flete["severidad"] != "informativo"
    ]
    for orden_id, fila in hallazgos.iterrows():
        estado = str(fila["estado_flete"])
        _registrar(
            session,
            periodo_id=periodo_id,
            codigo=f"WIILOG_FLETE_{estado}",
            descripcion=f"Comisión de flete de la orden {orden_id}: {estado}.",
            evidencia={
                "orden_id": str(orden_id),
                "estado": estado,
                "transportadora": _valor_texto(fila.get("transportadora")),
                "guia": _valor_texto(fila.get("guia")),
                "monto_en_juego_c": int(fila["monto_en_juego_c"]),
                "flete_neto_c": int(fila["flete_neto_c"]),
                "flete_movimientos": _valor_texto(
                    fila.get("flete_movimientos")
                ),
            },
            critico=str(fila["severidad"]) == "critico",
            gravedad=str(fila["severidad"]).upper(),
        )
        creados += 1
    return creados


def ejecutar_y_persistir_wiilog(
    session: Session,
    *,
    empresa_id: int,
    periodo_id: int,
    fuente_ordenes_id: int,
    fuente_wallet_id: int,
    ordenes_contenido: bytes,
    wallet_contenido: bytes,
    params: dict[str, Any] | None = None,
) -> EjecucionWiilog:
    periodo = _periodo_abierto(
        session,
        empresa_id=empresa_id,
        periodo_id=periodo_id,
    )

    carga_ordenes = registrar_carga(
        session,
        empresa_id=empresa_id,
        fuente_id=fuente_ordenes_id,
        periodo_id=periodo_id,
        contenido_hash=calcular_hash_contenido(ordenes_contenido),
    )
    carga_wallet = registrar_carga(
        session,
        empresa_id=empresa_id,
        fuente_id=fuente_wallet_id,
        periodo_id=periodo_id,
        contenido_hash=calcular_hash_contenido(wallet_contenido),
    )
    session.flush()

    ordenes = _leer_excel(ordenes_contenido, "órdenes")
    wallet = _leer_excel(wallet_contenido, "wallet")
    configuracion = params or cargar_parametros_wiilog()

    resultado = conciliar_wallet_wiilog(
        ordenes,
        wallet,
        configuracion,
        periodo.fecha_inicio,
        periodo.fecha_fin,
    )

    creados = _persistir_chequeos(
        session,
        periodo_id=periodo_id,
        resultado=resultado,
    )
    if not resultado.bloqueado:
        creados += _persistir_movimientos(
            session,
            periodo_id=periodo_id,
            resultado=resultado,
        )
        creados += _persistir_ff(
            session,
            periodo_id=periodo_id,
            resultado=resultado,
        )
        creados += _persistir_flete(
            session,
            periodo_id=periodo_id,
            resultado=resultado,
        )

    session.flush()
    return EjecucionWiilog(
        carga_ordenes_id=carga_ordenes.id,
        carga_wallet_id=carga_wallet.id,
        bloqueado=resultado.bloqueado,
        hallazgos_creados=creados,
        resumen=resultado.resumen,
    )


def listar_hallazgos_wiilog(
    session: Session,
    *,
    empresa_id: int,
    periodo_id: int,
) -> list[Hallazgo]:
    _periodo_abierto_o_cerrado(
        session,
        empresa_id=empresa_id,
        periodo_id=periodo_id,
    )
    statement = (
        select(Hallazgo)
        .where(
            Hallazgo.periodo_id == periodo_id,
            Hallazgo.motor_slug == MOTOR_SLUG,
            Hallazgo.codigo_regla.like("WIILOG_%"),
        )
        .order_by(Hallazgo.id)
    )
    return list(session.scalars(statement))


def _periodo_abierto_o_cerrado(
    session: Session,
    *,
    empresa_id: int,
    periodo_id: int,
) -> Periodo:
    periodo = session.get(Periodo, periodo_id)
    if periodo is None or periodo.empresa_id != empresa_id:
        raise ValueError("El período no pertenece a la empresa indicada.")
    return periodo
