"""Ejecuta las wallets de tienda y de pagos contra la base: cargas con hash, hallazgos y resumen.

Mismo patrón que wiilog/integracion.py. Decisiones del 30-sep (PANTALLA_WALLETS.md §7):
- El reporte de órdenes se comparte entre tiendas de la misma empresa: si su hash ya está cargado en la misma
  empresa, período y fuente, se reutiliza esa carga. En otro período o fuente sigue siendo duplicado.
- La bandeja muestra por defecto los hallazgos de la última carga de cada wallet.
"""
from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cargas import Carga, calcular_hash_contenido, registrar_carga
from app.core.empresas import Empresa
from app.core.hallazgos import Hallazgo, registrar_hallazgo_motor
from app.core.periodos import Periodo
from app.core.periodos.errors import PeriodoCerradoError

from ..pagos import conciliar_wallet_pagos
from ..tiendas import conciliar_wallet_tienda
from ..wiilog.integracion import cargar_parametros_wiilog, resolver_identificador_wallet
from .hallazgos import HallazgoNuevo, hallazgos_pagos, hallazgos_tienda, resultado_c0

MOTOR_SLUG = "conciliacion_wallets"
DOCS = Path(__file__).resolve().parents[4] / "docs" / "motores" / "conciliacion_wallets"
TIPO_TIENDA = "TIENDA"
TIPO_PAGOS = "SOLO_PAGOS"
_CORTE_EN_NOMBRE = re.compile(r"(\d{8})_(\d{6})")


class WalletNoConfiguradaError(ValueError):
    """La tienda o wallet no está en los parámetros, o es de otra empresa."""


class CargaDuplicadaError(ValueError):
    """El archivo ya se cargó en la empresa y no se puede reutilizar aquí."""


@dataclass(frozen=True)
class EjecucionWallet:
    carga_wallet_id: int
    carga_ordenes_id: int | None
    ordenes_reutilizadas: bool
    bloqueado: bool
    c0: dict[str, Any]
    hallazgos_creados: int
    hallazgos_por_gravedad: dict[str, int]
    resumen: dict[str, Any]
    corte_ordenes_usado: dict[str, str] | None = None


def _json(datos: Any) -> Any:
    """Deja el resumen del motor en tipos JSON (numpy, Decimal y fechas a texto o entero)."""

    def convertir(valor: object) -> object:
        if isinstance(valor, np.integer):
            return int(valor)
        if isinstance(valor, np.bool_):
            return bool(valor)
        if isinstance(valor, (Decimal, pd.Timestamp)):
            return str(valor)
        raise TypeError(f"Tipo no serializable: {type(valor).__name__}")

    return json.loads(json.dumps(datos, default=convertir))


def cargar_json(nombre: str) -> dict[str, Any]:
    return json.loads((DOCS / nombre).read_text(encoding="utf-8"))


def cargar_parametros_tienda() -> dict[str, Any]:
    return cargar_json("parametros_wallet_tienda.json")


def cargar_parametros_pagos() -> dict[str, Any]:
    return cargar_json("parametros_wallet_pagos.json")


def cargar_catalogo() -> dict[str, Any]:
    return cargar_json("catalogo_conceptos_wallets.json")


# ------------------------------------------------------------------ contexto


def periodo_de_empresa(session: Session, *, empresa_id: int, periodo_id: int) -> Periodo:
    periodo = session.get(Periodo, periodo_id)
    if periodo is None or periodo.empresa_id != empresa_id:
        raise ValueError("El período no pertenece a la empresa indicada.")
    return periodo


def _periodo_abierto(session: Session, *, empresa_id: int, periodo_id: int) -> Periodo:
    periodo = periodo_de_empresa(session, empresa_id=empresa_id, periodo_id=periodo_id)
    if periodo.cerrado:
        raise PeriodoCerradoError(
            "El período está cerrado. Reábrelo antes de ejecutar la conciliación."
        )
    return periodo


def nombre_empresa(session: Session, empresa_id: int) -> str | None:
    empresa = session.get(Empresa, empresa_id)
    return None if empresa is None else empresa.nombre


def _wallet_de_empresa(lista: list[dict], email: str, empresa: str | None, tipo: str) -> dict:
    wallet = next((w for w in lista if w["usuario_email"].lower() == email.strip().lower()), None)
    if wallet is None:
        raise WalletNoConfiguradaError(
            f"La {tipo} {email} no está en los parámetros de wallets. "
            "Elige una de la lista o pide que la agreguen a los parámetros."
        )
    if wallet.get("empresa") != empresa:
        raise WalletNoConfiguradaError(
            f"La {tipo} {wallet['nombre']} es de {wallet.get('empresa') or 'una empresa por confirmar'}. "
            "Cambia la empresa en el encabezado antes de conciliar."
        )
    return wallet


def catalogo_de_empresa(session: Session, empresa_id: int) -> dict[str, Any]:
    """Wallets que se pueden conciliar en la empresa, según los parámetros."""
    empresa = nombre_empresa(session, empresa_id)
    if empresa is None:
        raise ValueError("La empresa no existe.")

    def de_empresa(lista: list[dict], campos: tuple[str, ...]) -> list[dict]:
        return [{c: w.get(c) for c in campos} for w in lista if w.get("empresa") == empresa]

    return {
        "empresa": empresa,
        "wiilog": cargar_json("parametros_wallet_wiilog.json").get("empresa") == empresa,
        "tiendas": de_empresa(cargar_parametros_tienda()["tiendas"], ("usuario_email", "nombre", "rol")),
        "pagos": de_empresa(cargar_parametros_pagos()["wallets"], ("usuario_email", "nombre")),
    }


# -------------------------------------------------------------------- archivos


def _leer_excel(contenido: bytes, nombre: str) -> pd.DataFrame:
    if not contenido:
        raise ValueError(f"El archivo de {nombre} no puede estar vacío.")
    try:
        frame = pd.read_excel(io.BytesIO(contenido))
    except Exception as exc:
        raise ValueError(
            f"No se pudo leer el archivo de {nombre}. Confirma que sea un Excel válido exportado desde Dropi."
        ) from exc
    if frame.empty:
        raise ValueError(f"El archivo de {nombre} no puede estar vacío.")
    return frame


def corte_ordenes(texto: str | None, nombre_archivo: str | None) -> pd.Timestamp | None:
    """Hora de descarga del reporte: la escrita, o la del nombre del archivo (_AAAAMMDD_HHMMSS), o ninguna."""
    if texto and texto.strip():
        try:
            return pd.Timestamp(texto.strip())
        except ValueError as exc:
            raise ValueError(
                "La hora de descarga del reporte no es válida. Escríbela como AAAA-MM-DD HH:MM."
            ) from exc
    if nombre_archivo and (m := _CORTE_EN_NOMBRE.search(nombre_archivo)):
        corte = pd.to_datetime(m.group(1) + m.group(2), format="%Y%m%d%H%M%S", errors="coerce")
        return None if pd.isna(corte) else corte
    return None


def origen_corte_ordenes(texto: str | None, nombre_archivo: str | None) -> str:
    """De dónde sale el corte que usa el motor, en el mismo orden de corte_ordenes()."""
    if texto and texto.strip():
        return "formulario"
    if corte_ordenes(None, nombre_archivo) is not None:
        return "nombre_archivo"
    return "fecha_de_reporte"


def _corte_usado(resumen: dict | None, texto: str | None, nombre_archivo: str | None) -> dict[str, str] | None:
    """Corte que aplicó el motor; si C0 bloquea no hay resumen y tampoco corte."""
    if not resumen or "corte_reporte_ordenes" not in resumen:
        return None
    return {"valor": str(resumen["corte_reporte_ordenes"]), "origen": origen_corte_ordenes(texto, nombre_archivo)}


def _carga_de_ordenes(
    session: Session, *, empresa_id: int, periodo_id: int, fuente_id: int, contenido: bytes
) -> tuple[Carga, bool]:
    hash_ = calcular_hash_contenido(contenido)
    existente = session.scalar(
        select(Carga).where(Carga.empresa_id == empresa_id, Carga.contenido_hash == hash_)
    )
    if existente is None:
        carga = registrar_carga(
            session, empresa_id=empresa_id, fuente_id=fuente_id, periodo_id=periodo_id, contenido_hash=hash_
        )
        return carga, False
    if existente.periodo_id == periodo_id and existente.fuente_id == fuente_id:
        return existente, True
    raise CargaDuplicadaError(
        "Este reporte de órdenes ya se cargó en la empresa para otro período o con otra fuente. "
        "Usa el reporte del período que estás conciliando."
    )


def _carga_de_wallet(
    session: Session, *, empresa_id: int, periodo_id: int, fuente_id: int, contenido: bytes
) -> Carga:
    carga = registrar_carga(
        session,
        empresa_id=empresa_id,
        fuente_id=fuente_id,
        periodo_id=periodo_id,
        contenido_hash=calcular_hash_contenido(contenido),
    )
    session.flush()
    return carga


# ------------------------------------------------------------------ hallazgos


def _persistir(
    session: Session,
    *,
    periodo_id: int,
    wallet: dict,
    tipo_wallet: str,
    carga_wallet_id: int,
    hallazgos: list[HallazgoNuevo],
) -> dict[str, int]:
    conteo: dict[str, int] = {}
    for h in hallazgos:
        registrar_hallazgo_motor(
            session,
            periodo_id=periodo_id,
            motor_slug=MOTOR_SLUG,
            codigo_regla=h.codigo,
            descripcion=h.descripcion,
            evidencia=_json(
                {
                    "wallet": wallet["usuario_email"],
                    "wallet_nombre": wallet.get("nombre"),
                    "tipo_wallet": tipo_wallet,
                    "gravedad": h.gravedad,
                    "carga_wallet_id": carga_wallet_id,
                    **h.evidencia,
                }
            ),
            critico=h.critico,
        )
        conteo[h.gravedad] = conteo.get(h.gravedad, 0) + 1
    session.flush()
    return conteo


def ejecutar_y_persistir_tienda(
    session: Session,
    *,
    empresa_id: int,
    periodo_id: int,
    tienda_email: str,
    fuente_wallet_id: int,
    fuente_ordenes_id: int,
    wallet_contenido: bytes,
    ordenes_contenido: bytes,
    nombre_ordenes: str | None = None,
    corte: str | None = None,
) -> EjecucionWallet:
    periodo = _periodo_abierto(session, empresa_id=empresa_id, periodo_id=periodo_id)
    params = resolver_identificador_wallet(cargar_parametros_tienda())
    catalogo = resolver_identificador_wallet(cargar_catalogo())
    tienda = _wallet_de_empresa(params["tiendas"], tienda_email, nombre_empresa(session, empresa_id), "tienda")
    corte_reporte = corte_ordenes(corte, nombre_ordenes)
    # Antes de registrar cargas: si falta la configuración de Wiilog no debe quedar nada guardado.
    tarifas_ff = cargar_parametros_wiilog()["fulfillment"]["tarifas_por_bodega"]

    carga_ordenes, reutilizada = _carga_de_ordenes(
        session, empresa_id=empresa_id, periodo_id=periodo_id, fuente_id=fuente_ordenes_id, contenido=ordenes_contenido
    )
    carga_wallet = _carga_de_wallet(
        session, empresa_id=empresa_id, periodo_id=periodo_id, fuente_id=fuente_wallet_id, contenido=wallet_contenido
    )

    resultado = conciliar_wallet_tienda(
        _leer_excel(ordenes_contenido, "órdenes"),
        _leer_excel(wallet_contenido, "wallet"),
        params,
        catalogo,
        tienda,
        periodo.fecha_inicio,
        periodo.fecha_fin,
        tarifas_ff,
        corte_ordenes=corte_reporte,
    )
    hallazgos = hallazgos_tienda(resultado)
    conteo = _persistir(
        session,
        periodo_id=periodo_id,
        wallet=tienda,
        tipo_wallet=TIPO_TIENDA,
        carga_wallet_id=carga_wallet.id,
        hallazgos=hallazgos,
    )
    return EjecucionWallet(
        carga_wallet_id=carga_wallet.id,
        carga_ordenes_id=carga_ordenes.id,
        ordenes_reutilizadas=reutilizada,
        bloqueado=resultado.bloqueado,
        c0=_json(resultado_c0(resultado.chequeos)),
        hallazgos_creados=len(hallazgos),
        hallazgos_por_gravedad=conteo,
        resumen=_json(resultado.resumen),
        corte_ordenes_usado=_corte_usado(resultado.resumen, corte, nombre_ordenes),
    )


def ejecutar_y_persistir_pagos(
    session: Session,
    *,
    empresa_id: int,
    periodo_id: int,
    wallet_email: str,
    fuente_wallet_id: int,
    wallet_contenido: bytes,
) -> EjecucionWallet:
    periodo = _periodo_abierto(session, empresa_id=empresa_id, periodo_id=periodo_id)
    params = resolver_identificador_wallet(cargar_parametros_pagos())
    catalogo = resolver_identificador_wallet(cargar_catalogo())
    wallet = _wallet_de_empresa(params["wallets"], wallet_email, nombre_empresa(session, empresa_id), "wallet de pagos")

    carga_wallet = _carga_de_wallet(
        session, empresa_id=empresa_id, periodo_id=periodo_id, fuente_id=fuente_wallet_id, contenido=wallet_contenido
    )
    resultado = conciliar_wallet_pagos(
        _leer_excel(wallet_contenido, "wallet"),
        params,
        catalogo,
        wallet,
        periodo.fecha_inicio,
        periodo.fecha_fin,
    )
    hallazgos = hallazgos_pagos(resultado)
    conteo = _persistir(
        session,
        periodo_id=periodo_id,
        wallet=wallet,
        tipo_wallet=TIPO_PAGOS,
        carga_wallet_id=carga_wallet.id,
        hallazgos=hallazgos,
    )
    return EjecucionWallet(
        carga_wallet_id=carga_wallet.id,
        carga_ordenes_id=None,
        ordenes_reutilizadas=False,
        bloqueado=resultado.bloqueado,
        c0=_json(resultado_c0(resultado.chequeos)),
        hallazgos_creados=len(hallazgos),
        hallazgos_por_gravedad=conteo,
        resumen=_json(resultado.resumen),
    )


def listar_hallazgos_wallet(
    session: Session,
    *,
    empresa_id: int,
    periodo_id: int,
    prefijo: str,
    wallet: str | None = None,
    todas_las_cargas: bool = False,
) -> list[Hallazgo]:
    """Hallazgos de tiendas (TIENDA) o pagos (PAGOS); por defecto solo los de la última carga de cada wallet."""
    periodo_de_empresa(session, empresa_id=empresa_id, periodo_id=periodo_id)
    hallazgos = list(
        session.scalars(
            select(Hallazgo)
            .where(
                Hallazgo.periodo_id == periodo_id,
                Hallazgo.motor_slug == MOTOR_SLUG,
                Hallazgo.codigo_regla.like(f"{prefijo}\\_%", escape="\\"),
            )
            .order_by(Hallazgo.id)
        )
    )
    if wallet:
        hallazgos = [h for h in hallazgos if (h.evidencia or {}).get("wallet") == wallet.strip().lower()]
    if todas_las_cargas:
        return hallazgos
    ultima: dict[str, int] = {}
    for h in hallazgos:
        ev = h.evidencia or {}
        ultima[ev.get("wallet")] = max(ultima.get(ev.get("wallet"), 0), ev.get("carga_wallet_id") or 0)
    return [h for h in hallazgos if (h.evidencia or {}).get("carga_wallet_id") == ultima[(h.evidencia or {}).get("wallet")]]