from __future__ import annotations

import io
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.hallazgos import Hallazgo, HallazgoMotorNuevo, sincronizar_hallazgos_motor
from app.core.periodos import Periodo
from app.core.periodos.errors import PeriodoCerradoError

from ..cargas import MENSAJE_CONCILIACION_REPETIDA, ConciliacionRepetidaError, carga_reutilizable
from ..reconciliation_model import WiilogReconciliation
from .motor import ResultadoWiilog, conciliar_wallet_wiilog
from .normalizar import pesos


MOTOR_SLUG = "conciliacion_wallets"
PARAMS_PATH = (
    Path(__file__).resolve().parents[4]
    / "docs"
    / "motores"
    / "conciliacion_wallets"
    / "parametros_wallet_wiilog.json"
)
CATALOGO_COMUN_PATH = PARAMS_PATH.parent / "catalogo_conceptos_wallets.json"


MENSAJE_CONFIGURACION_FALTANTE = (
    "Falta configurar la wallet principal de Wiilog. Pide a TI que la defina."
)


class ConfiguracionWiilogFaltanteError(RuntimeError):
    """Falta el identificador de la wallet principal; se detecta antes de registrar cargas."""


@dataclass(frozen=True)
class EjecucionWiilog:
    carga_ordenes_id: int
    carga_wallet_id: int
    ordenes_reutilizadas: bool
    wallet_reutilizada: bool
    bloqueado: bool
    c0: dict[str, Any]
    hallazgos_creados: int
    hallazgos_por_gravedad: dict[str, int]
    resumen: dict[str, Any]
    sincronizacion: dict[str, int]


def _resultado_c0(chequeos: list) -> dict[str, Any]:
    """Contrato estructurado del C0 para la pantalla, sin cambiar reglas del motor."""
    por_codigo = {chequeo.codigo: chequeo for chequeo in chequeos}
    saldo = por_codigo["C0_SALDO"]
    cobertura = por_codigo.get("C0_COBERTURA")
    return {
        "cuadra": saldo.estado == "EN_ORDEN",
        "mensaje": saldo.mensaje,
        **saldo.detalle,
        "cobertura": None
        if cobertura is None
        else {
            "estado": cobertura.estado,
            "mensaje": cobertura.mensaje,
            **cobertura.detalle,
        },
    }


WIILOG_WALLET_EMAIL_PLACEHOLDER = "{{WIILOG_WALLET_PRINCIPAL_EMAIL}}"


def _resolver_identificador_wallet(
    valor: object,
    *,
    wallet_principal_email: str,
) -> object:
    if isinstance(valor, str):
        return valor.replace(
            WIILOG_WALLET_EMAIL_PLACEHOLDER,
            wallet_principal_email,
        )
    if isinstance(valor, list):
        return [
            _resolver_identificador_wallet(
                item,
                wallet_principal_email=wallet_principal_email,
            )
            for item in valor
        ]
    if isinstance(valor, dict):
        return {
            clave: _resolver_identificador_wallet(
                item,
                wallet_principal_email=wallet_principal_email,
            )
            for clave, item in valor.items()
        }
    return valor


def resolver_identificador_wallet(
    valor: object,
    *,
    wallet_principal_email: str | None = None,
) -> object:
    """Resuelve el identificador privado de Wiilog únicamente en runtime."""
    identificador = (
        wallet_principal_email
        if wallet_principal_email is not None
        else os.getenv("WIILOG_WALLET_PRINCIPAL_EMAIL", "")
    ).strip()
    if not identificador:
        raise ConfiguracionWiilogFaltanteError(
            f"{MENSAJE_CONFIGURACION_FALTANTE} "
            "Variable: WIILOG_WALLET_PRINCIPAL_EMAIL, fuera de Git."
        )
    return _resolver_identificador_wallet(
        valor,
        wallet_principal_email=identificador,
    )


def cargar_parametros_wiilog(
    *,
    wallet_principal_email: str | None = None,
) -> dict[str, Any]:
    parametros = json.loads(PARAMS_PATH.read_text(encoding="utf-8"))
    return resolver_identificador_wallet(
        parametros,
        wallet_principal_email=wallet_principal_email,
    )


def cargar_catalogo_comun(
    *,
    wallet_principal_email: str | None = None,
) -> dict[str, Any]:
    catalogo = json.loads(CATALOGO_COMUN_PATH.read_text(encoding="utf-8"))
    return resolver_identificador_wallet(
        catalogo,
        wallet_principal_email=wallet_principal_email,
    )


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
    # Serializa las conciliaciones del período hasta el commit: el ID de ejecución
    # debe representar el mismo orden que la sincronización de los hallazgos.
    periodo = session.scalar(
        select(Periodo).where(Periodo.id == periodo_id, Periodo.empresa_id == empresa_id)
        .with_for_update().execution_options(populate_existing=True)
    )
    if periodo is None or periodo.empresa_id != empresa_id:
        raise ValueError("El período no pertenece a la empresa indicada.")
    if periodo.cerrado:
        raise PeriodoCerradoError(
            "El período está cerrado. Reábrelo antes de ejecutar la conciliación."
        )
    return periodo


ALCANCE_WIILOG = "WIILOG|"


@dataclass
class _Lote:
    """Hallazgos de una carga, con su clave estable (decisión 0008): se sincronizan al final."""

    carga_wallet_id: int
    conciliacion_id: int
    nuevos: list[HallazgoMotorNuevo]
    conteo: dict[str, int]


def _registrar(
    session: Session,
    *,
    periodo_id: int,
    codigo: str,
    descripcion: str,
    evidencia: dict[str, Any],
    critico: bool,
    gravedad: str,
    lote: _Lote,
) -> None:
    # La gravedad va en la evidencia para la bandeja (PANTALLA_WALLETS.md §2.2); no cambia qué es hallazgo.
    evidencia = {
        **evidencia, "wallet": "WIILOG", "gravedad": gravedad,
        "carga_wallet_id": lote.carga_wallet_id, "conciliacion_id": lote.conciliacion_id,
    }
    lote.conteo[gravedad] = lote.conteo.get(gravedad, 0) + 1
    identificador = evidencia.get("orden_id") or evidencia.get("mov_id") or "-"
    lote.nuevos.append(
        HallazgoMotorNuevo(
            clave=f"{ALCANCE_WIILOG}{codigo}|{identificador}",
            codigo_regla=codigo,
            descripcion=descripcion,
            evidencia=evidencia,
            critico=critico,
        )
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
    lote: _Lote,
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
            lote=lote,
        )
        creados += 1
    return creados


def _persistir_movimientos(
    session: Session,
    *,
    periodo_id: int,
    resultado: ResultadoWiilog,
    lote: _Lote,
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
                "tipo": "REVISAR_MOVIMIENTO",
                "mov_id": int(fila.mov_id),
                "fecha": str(fila.fecha),
                "concepto": _valor_texto(fila.concepto),
                "texto_dropi": _valor_texto(fila.descripcion),
                "entrada_salida": _valor_texto(fila.tipo),
                "texto_nuevo": fila.concepto == "SIN_CONCEPTO",
                "flujo": _valor_texto(fila.flujo),
                "ingreso_egreso": _valor_texto(fila.ingreso_egreso),
                "unidad_negocio": _valor_texto(fila.unidad_negocio),
                "categoria": _valor_texto(fila.categoria),
                "monto": str(pesos(int(fila.neto_c))),
                "monto_c": int(fila.monto_c),
                "tercero": _valor_texto(fila.tercero),
                "requiere_observacion": bool(fila.requiere_observacion),
            },
            critico=False,
            gravedad="REVISAR",
            lote=lote,
        )
        creados += 1
    return creados


def _persistir_ff(
    session: Session,
    *,
    periodo_id: int,
    resultado: ResultadoWiilog,
    lote: _Lote,
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
            lote=lote,
        )
        creados += 1
    return creados


def _persistir_flete(
    session: Session,
    *,
    periodo_id: int,
    resultado: ResultadoWiilog,
    lote: _Lote,
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
            lote=lote,
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
    usuario_id: int,
    params: dict[str, Any] | None = None,
    catalogo: dict[str, Any] | None = None,
) -> EjecucionWiilog:
    periodo = _periodo_abierto(
        session,
        empresa_id=empresa_id,
        periodo_id=periodo_id,
    )
    # Antes de registrar cargas: si falta configuración no debe quedar nada guardado.
    configuracion = params or cargar_parametros_wiilog()
    catalogo_comun = catalogo or cargar_catalogo_comun()

    # Igual que Tiendas: el mismo reporte de órdenes se reutiliza en la misma empresa, período y fuente.
    carga_ordenes, ordenes_reutilizadas = carga_reutilizable(
        session, empresa_id=empresa_id, periodo_id=periodo_id, fuente_id=fuente_ordenes_id,
        contenido=ordenes_contenido, que="reporte de órdenes",
    )
    carga_wallet, wallet_reutilizada = carga_reutilizable(
        session, empresa_id=empresa_id, periodo_id=periodo_id, fuente_id=fuente_wallet_id,
        contenido=wallet_contenido, que="archivo de wallet",
    )
    previous = session.scalar(
        select(WiilogReconciliation.id).where(
            WiilogReconciliation.periodo_id == periodo_id,
            WiilogReconciliation.carga_ordenes_id == carga_ordenes.id,
            WiilogReconciliation.carga_wallet_id == carga_wallet.id,
        )
    )
    if previous is not None:
        raise ConciliacionRepetidaError(MENSAJE_CONCILIACION_REPETIDA)

    ordenes = _leer_excel(ordenes_contenido, "órdenes")
    wallet = _leer_excel(wallet_contenido, "wallet")

    resultado = conciliar_wallet_wiilog(
        ordenes,
        wallet,
        configuracion,
        periodo.fecha_inicio,
        periodo.fecha_fin,
        catalogo=catalogo_comun,
    )

    # También se guarda si el motor no produce hallazgos o C0 bloquea.
    # El endpoint confirma cargas, ejecución y hallazgos en una sola transacción.
    reconciliation = WiilogReconciliation(
        periodo_id=periodo_id, carga_ordenes_id=carga_ordenes.id,
        carga_wallet_id=carga_wallet.id, usuario_id=usuario_id,
    )
    session.add(reconciliation)
    session.flush()
    lote = _Lote(
        carga_wallet_id=carga_wallet.id, conciliacion_id=reconciliation.id, nuevos=[], conteo={},
    )
    creados = _persistir_chequeos(
        session,
        periodo_id=periodo_id,
        resultado=resultado,
        lote=lote,
    )
    if not resultado.bloqueado:
        creados += _persistir_movimientos(
            session,
            periodo_id=periodo_id,
            resultado=resultado,
            lote=lote,
        )
        creados += _persistir_ff(
            session,
            periodo_id=periodo_id,
            resultado=resultado,
            lote=lote,
        )
        creados += _persistir_flete(
            session,
            periodo_id=periodo_id,
            resultado=resultado,
            lote=lote,
        )

    claves = [h.clave for h in lote.nuevos]
    if len(claves) != len(set(claves)):
        raise RuntimeError("Dos hallazgos de Wiilog quedaron con la misma clave; revisa el motor.")
    # Si C0 bloquea solo se sincronizan los chequeos C0: lo demás no se evaluó y no se resuelve.
    alcance = f"{ALCANCE_WIILOG}WIILOG_C0_" if resultado.bloqueado else ALCANCE_WIILOG
    sincronizacion = sincronizar_hallazgos_motor(
        session,
        periodo_id=periodo_id,
        motor_slug=MOTOR_SLUG,
        alcance_clave=alcance,
        hallazgos=lote.nuevos,
        usuario_id=usuario_id,
    )
    return EjecucionWiilog(
        carga_ordenes_id=carga_ordenes.id,
        carga_wallet_id=carga_wallet.id,
        ordenes_reutilizadas=ordenes_reutilizadas,
        wallet_reutilizada=wallet_reutilizada,
        bloqueado=resultado.bloqueado,
        c0=_resultado_c0(resultado.chequeos),
        hallazgos_creados=creados,
        hallazgos_por_gravedad=lote.conteo,
        resumen=resultado.resumen,
        sincronizacion=vars(sincronizacion),
    )


def listar_hallazgos_wiilog(
    session: Session,
    *,
    empresa_id: int,
    periodo_id: int,
    todas_las_cargas: bool = False,
) -> list[Hallazgo]:
    """Por defecto, los de la última ejecución, aunque reutilice una carga antigua."""
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
    hallazgos = list(session.scalars(statement))
    if todas_las_cargas:
        return hallazgos
    latest = session.scalar(
        select(WiilogReconciliation.id)
        .where(WiilogReconciliation.periodo_id == periodo_id)
        .order_by(WiilogReconciliation.id.desc()).limit(1)
    )
    if latest is not None:
        return [h for h in hallazgos if (h.evidencia or {}).get("conciliacion_id") == latest]
    # Períodos anteriores a la migración: conservar la vista hasta su primera
    # ejecución trazable, sin inventar parejas a partir de archivos sueltos.
    cargas = [(h.evidencia or {}).get("carga_wallet_id") for h in hallazgos]
    ultima = max((c for c in cargas if c), default=None)
    if ultima is None:
        return hallazgos
    return [h for h, carga in zip(hallazgos, cargas) if carga == ultima]


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
