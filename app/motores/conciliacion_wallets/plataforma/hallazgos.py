"""Qué resultado del motor se vuelve hallazgo, con qué gravedad y qué evidencia. Python puro, sin base de datos.

Regla única (PANTALLA_WALLETS.md §2.2): es hallazgo lo que el motor marca con gravedad distinta de OK.
Gravedades: CRITICO, MEDIO, INFORMATIVO y REVISAR (movimiento que el conciliador confirma con observación).

Dos motivos de "fuera del reporte" se guardan como un solo hallazgo por carga de wallet (decisiones 30-sep):
ORDEN_ANTERIOR_AL_REPORTE (miles de movimientos de meses anteriores) y NO_ENCONTRADA.

Montos de la evidencia en texto decimal ("34998.00"), nunca float.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from ..tiendas.reglas import GRAVEDAD
from ..wiilog import normalizar as n

CRITICO = "CRITICO"
MEDIO = "MEDIO"
INFORMATIVO = "INFORMATIVO"
REVISAR = "REVISAR"
_ORDEN_GRAVEDAD = ["OK", INFORMATIVO, MEDIO, CRITICO]

TIPO_REVISAR_MOVIMIENTO = "REVISAR_MOVIMIENTO"
REEMPLAZADAS = "Reembolsos de órdenes reemplazadas"
OTROS_NO_ENCONTRADOS = "Otros movimientos de órdenes que no están en el reporte"


@dataclass(frozen=True)
class HallazgoNuevo:
    codigo: str
    descripcion: str
    gravedad: str
    evidencia: dict[str, Any] = field(default_factory=dict)

    @property
    def critico(self) -> bool:
        return self.gravedad == CRITICO


# ------------------------------------------------------------------ valores


def pesos(centavos: object) -> str | None:
    if centavos is None or pd.isna(centavos):
        return None
    return str(n.pesos(int(centavos)))


def _texto(valor: object) -> str | None:
    if valor is None or pd.isna(valor):
        return None
    return str(valor)


def _fecha(valor: object) -> str | None:
    if valor is None or pd.isna(valor):
        return None
    return str(pd.Timestamp(valor))


def _entero(valor: object) -> int:
    return int(valor) if valor is not None and not pd.isna(valor) else 0


# ----------------------------------------------------------------------- C0


def resultado_c0(chequeos: list) -> dict[str, Any]:
    """Lo que la pantalla muestra del C0: saldos, si cuadra y la advertencia de cobertura."""
    por_codigo = {c.codigo: c for c in chequeos}
    saldo = por_codigo["C0_SALDO"]
    cobertura = por_codigo.get("C0_COBERTURA")
    return {
        "cuadra": saldo.estado == "EN_ORDEN",
        "mensaje": saldo.mensaje,
        **saldo.detalle,
        "cobertura": None
        if cobertura is None
        else {"estado": cobertura.estado, "mensaje": cobertura.mensaje, **cobertura.detalle},
    }


def hallazgos_chequeos(prefijo: str, chequeos: list) -> list[HallazgoNuevo]:
    return [
        HallazgoNuevo(
            codigo=f"{prefijo}_{c.codigo}",
            descripcion=c.mensaje,
            gravedad=CRITICO if c.estado == "BLOQUEADO" else INFORMATIVO,
            evidencia={"estado": c.estado, "detalle": c.detalle},
        )
        for c in chequeos
        if c.estado != "EN_ORDEN"
    ]


# --------------------------------------------------------------- movimientos


def hallazgos_movimientos(prefijo: str, mov: pd.DataFrame) -> list[HallazgoNuevo]:
    revisar = mov[mov.requiere_revision]
    return [
        HallazgoNuevo(
            codigo=f"{prefijo}_MOVIMIENTO_REVISAR",
            descripcion="El movimiento requiere revisión: confirma su categoría y escribe la observación antes del cierre.",
            gravedad=REVISAR,
            evidencia={
                "tipo": TIPO_REVISAR_MOVIMIENTO,
                "mov_id": int(f.mov_id),
                "fecha": _fecha(f.fecha),
                "concepto": _texto(f.concepto),
                "texto_dropi": _texto(f.descripcion),
                "entrada_salida": _texto(f.tipo),
                # Texto que el catálogo no reconoce: llega sin propuesta y el conciliador lo categoriza.
                "texto_nuevo": f.concepto == "SIN_CONCEPTO",
                "ingreso_egreso": None if f.concepto == "SIN_CONCEPTO" else _texto(f.ingreso_egreso),
                "unidad_negocio": _texto(f.unidad_negocio),
                "categoria": _texto(f.categoria),
                "tercero": _texto(f.tercero),
                "tipo_tercero": _texto(f.tipo_tercero),
                "monto": pesos(f.neto_c),
                "observacion_sugerida": _texto(f.observacion) or None,
            },
        )
        for f in revisar.itertuples(index=False)
    ]


# ---------------------------------------------------------- reglas de tienda


def _por_orden(regla: str, nombre: str, df: pd.DataFrame | None, evidencia) -> list[HallazgoNuevo]:
    if df is None:
        return []
    out = []
    for orden_id, f in df[df.gravedad != "OK"].iterrows():
        estado = str(f.estado)
        out.append(
            HallazgoNuevo(
                codigo=f"TIENDA_{regla}_{estado}",
                descripcion=f"{nombre} de la orden {orden_id}: {estado}.",
                gravedad=str(f.gravedad),
                evidencia={
                    "regla": regla,
                    "orden_id": str(orden_id),
                    "estado": estado,
                    "monto_en_juego": pesos(f.monto_en_juego_c),
                    **evidencia(f),
                },
            )
        )
    return out


def _sin_recaudo(df: pd.DataFrame | None) -> list[HallazgoNuevo]:
    if df is None:
        return []
    out = []
    for orden_id, f in df[df.gravedad != "OK"].iterrows():
        # El código lleva el estado que da la gravedad; si empatan, el del reembolso.
        g_cobro = _ORDEN_GRAVEDAD.index(GRAVEDAD.get(f.estado_cobro, "OK"))
        g_reembolso = _ORDEN_GRAVEDAD.index(GRAVEDAD.get(f.estado_reembolso, "OK"))
        estado = str(f.estado_reembolso if g_reembolso >= g_cobro else f.estado_cobro)
        out.append(
            HallazgoNuevo(
                codigo=f"TIENDA_T2_{estado}",
                descripcion=f"Orden sin recaudo {orden_id}: cobro {f.estado_cobro}, reembolso {f.estado_reembolso}.",
                gravedad=str(f.gravedad),
                evidencia={
                    "regla": "T2",
                    "orden_id": str(orden_id),
                    "estado": estado,
                    "estatus": _texto(f.estatus),
                    "estado_cobro": str(f.estado_cobro),
                    "estado_reembolso": str(f.estado_reembolso),
                    "cobro_esperado": pesos(f.cobro_esperado_c),
                    "cobrado": pesos(f.cobrado_c),
                    "n_cobros": _entero(f.n_cobros),
                    "reembolso_esperado": pesos(f.reembolso_esperado_c),
                    "reembolsado": pesos(f.reembolsado_c),
                    "monto_en_juego": pesos(f.monto_en_juego_c),
                },
            )
        )
    return out


def _por_concepto(m: pd.DataFrame) -> dict[str, dict[str, Any]]:
    g = m.groupby("concepto").agg(movimientos=("mov_id", "size"), neto_c=("neto_c", "sum"))
    return {str(c): {"movimientos": int(v.movimientos), "neto": pesos(v.neto_c)} for c, v in g.iterrows()}


def _grupo(m: pd.DataFrame, nombre: str, *, por_concepto: bool) -> dict[str, Any]:
    grupo = {
        "nombre": nombre,
        "movimientos": int(len(m)),
        "neto": pesos(m.neto_c.sum()),
        "ordenes": sorted(m.orden_id.dropna().astype(str).unique().tolist()),
    }
    if por_concepto:
        grupo["por_concepto"] = _por_concepto(m)
    return grupo


def _anteriores(m: pd.DataFrame) -> HallazgoNuevo:
    return HallazgoNuevo(
        codigo="TIENDA_FUERA_ORDEN_ANTERIOR_AL_REPORTE",
        descripcion=(
            f"{len(m)} movimientos de órdenes anteriores al reporte: "
            "carga el reporte de órdenes del mes anterior."
        ),
        gravedad=INFORMATIVO,
        evidencia={
            "motivo": "ORDEN_ANTERIOR_AL_REPORTE",
            "movimientos": int(len(m)),
            "ordenes": int(m.orden_id.nunique()),
            "neto": pesos(m.neto_c.sum()),
            "por_concepto": _por_concepto(m),
        },
    )


def _no_encontradas(m: pd.DataFrame) -> HallazgoNuevo:
    reemplazada = (m.concepto == "REEMBOLSO_CAMBIO_ESTATUS") & m.descripcion.map(n.texto).str.contains("REEMPLAZADA")
    reemplazadas, otros = m[reemplazada], m[~reemplazada]
    return HallazgoNuevo(
        codigo="TIENDA_FUERA_NO_ENCONTRADA",
        descripcion=(
            f"{len(m)} movimientos de órdenes que no están en el reporte: "
            f"{len(reemplazadas)} reembolsos de órdenes reemplazadas (el reporte de Dropi no incluye las "
            f"órdenes reemplazadas) y {len(otros)} otros movimientos. Revisa las órdenes del segundo grupo."
        ),
        gravedad=str(m.gravedad.iloc[0]),
        evidencia={
            "motivo": "NO_ENCONTRADA",
            "movimientos": int(len(m)),
            "neto": pesos(m.neto_c.sum()),
            "reemplazadas": _grupo(reemplazadas, REEMPLAZADAS, por_concepto=False),
            "otros": _grupo(otros, OTROS_NO_ENCONTRADOS, por_concepto=True),
        },
    )


def _fuera_del_reporte(df: pd.DataFrame | None) -> list[HallazgoNuevo]:
    if df is None:
        return []
    df = df[df.gravedad != "OK"]
    out = []
    if not (m := df[df.motivo == "ORDEN_ANTERIOR_AL_REPORTE"]).empty:
        out.append(_anteriores(m))
    if not (m := df[df.motivo == "NO_ENCONTRADA"]).empty:
        out.append(_no_encontradas(m))
    for f in df[~df.motivo.isin(["ORDEN_ANTERIOR_AL_REPORTE", "NO_ENCONTRADA"])].itertuples(index=False):
        out.append(
            HallazgoNuevo(
                codigo=f"TIENDA_FUERA_{f.motivo}",
                descripcion=f"Movimiento {f.mov_id} ({f.concepto}) de la orden {f.orden_id}: {f.motivo}.",
                gravedad=str(f.gravedad),
                evidencia={
                    "motivo": str(f.motivo),
                    "mov_id": int(f.mov_id),
                    "fecha": _fecha(f.fecha),
                    "concepto": str(f.concepto),
                    "orden_id": _texto(f.orden_id),
                    "neto": pesos(f.neto_c),
                },
            )
        )
    return out


def hallazgos_tienda(r) -> list[HallazgoNuevo]:
    """Hallazgos de una conciliación de tienda (ResultadoTienda). Si C0 bloquea, solo el C0."""
    out = hallazgos_chequeos("TIENDA", r.chequeos)
    if r.bloqueado:
        return out
    out += _por_orden(
        "T1",
        "Ganancia",
        r.ganancia,
        lambda f: {
            "estatus": _texto(f.estatus),
            "tipo_envio": _texto(f.tipo_envio),
            "esperado": pesos(f.esperado_c),
            "pagado": pesos(f.pagado_c),
            "corregido": pesos(f.corregido_c),
            "neto": pesos(f.neto_c),
            "n_pagos": _entero(f.n_pagos),
        },
    )
    out += _sin_recaudo(r.sin_recaudo)
    out += _por_orden(
        "T3",
        "Devolución con recaudo",
        r.devoluciones,
        lambda f: {
            "estatus": _texto(f.estatus),
            "transportadora": _texto(f.transportadora),
            "cobrado": pesos(f.cobrado_c),
            "cobro_esperado": pesos(f.cobro_esperado_c),
            "precio_flete": pesos(f.precio_flete_c),
            "n_cobros": _entero(f.n_cobros),
        },
    )
    out += _por_orden(
        "T4",
        "Fulfillment",
        r.fulfillment,
        lambda f: {
            "estatus": _texto(f.estatus),
            "bodega": _texto(f.bodega),
            "cobrado": pesos(f.cobrado_c),
            "reversado": pesos(f.reversado_c),
            "neto": pesos(f.neto_c),
            "tarifa": pesos(f.tarifa_c),
            "n_cobros": _entero(f.n_cobros),
        },
    )
    out += _fuera_del_reporte(r.fuera_del_reporte)
    out += hallazgos_movimientos("TIENDA", r.movimientos)
    return out


def hallazgos_pagos(r) -> list[HallazgoNuevo]:
    """Hallazgos de una wallet de solo pagos (ResultadoPagos): C0 y movimientos por revisar."""
    out = hallazgos_chequeos("PAGOS", r.chequeos)
    if r.bloqueado:
        return out
    return out + hallazgos_movimientos("PAGOS", r.movimientos)
