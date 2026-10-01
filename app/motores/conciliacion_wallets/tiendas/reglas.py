"""Reglas de conciliación de wallets de tienda contra el reporte de órdenes.

T1 Ganancia        (DROPSHIPPER y PROVEEDOR)  ¿Dropi pagó lo que debía, una sola vez?
T2 Orden sin recaudo (DROPSHIPPER)            ¿El cobro de la orden es producto + flete? ¿Devolvió lo que debía?
T3 Devolución con recaudo (DROPSHIPPER)       ¿Cobró el flete de devolución una sola vez y por el valor de su tabla?
T4 Fulfillment     (PROVEEDOR)                ¿Cobró la tarifa de la bodega una sola vez y solo cuando correspondía?

Criterio de gravedad (las tiendas son del grupo): plata que Dropi le debe a la tienda = CRÍTICO;
cobro de más = MEDIO; lo demás = INFORMATIVO.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

import numpy as np
import pandas as pd

from ..wiilog import normalizar as n

GRAVEDAD = {
    "SIN_PAGO": "CRITICO",
    "DIFERENCIA_VALOR": "CRITICO",
    "SIN_REEMBOLSO": "CRITICO",
    "REEMBOLSO_PARCIAL": "CRITICO",
    "REEMBOLSO_NO_ESPERADO": "INFORMATIVO",
    "PAGO_SIN_ENTREGA": "MEDIO",
    "DUPLICADA": "INFORMATIVO",
    "DUPLICADO": "MEDIO",
    "COBRO_DUPLICADO": "MEDIO",
    "DIFERENCIA_COBRO": "MEDIO",
    "DIFERENCIA_TARIFA": "MEDIO",
    "COBRO_NO_CORRESPONDE": "MEDIO",
    "COBRO_ANTICIPADO": "INFORMATIVO",
    "COBRO_MAYOR_AL_FLETE": "MEDIO",
    "SIN_COBRO": "INFORMATIVO",
}


def movimientos_por_orden(mov: pd.DataFrame) -> pd.DataFrame:
    """Suma (con signo), cuenta y primera fecha de cada concepto por orden."""
    m = mov[mov.orden_id.notna()]
    suma = m.pivot_table(index="orden_id", columns="concepto", values="neto_c", aggfunc="sum", fill_value=0)
    cuenta = m.pivot_table(index="orden_id", columns="concepto", values="neto_c", aggfunc="count", fill_value=0).add_prefix("n_")
    primera = m.pivot_table(index="orden_id", columns="concepto", values="fecha", aggfunc="min").add_prefix("f_")
    return suma.join(cuenta).join(primera)


def _col(df: pd.DataFrame, nombre: str, defecto=0):
    return df[nombre] if nombre in df else pd.Series(defecto, index=df.index)


# --------------------------------------------------------------------- T1 ganancia


def ganancia(ordenes: pd.DataFrame, por_orden: pd.DataFrame, tienda: dict, params: dict, corte_wallet, corte_ordenes):
    cfg = params["ganancia"]
    rol = tienda["rol"]
    concepto = "GANANCIA_DROPSHIPPER" if rol == "DROPSHIPPER" else "GANANCIA_PROVEEDOR"
    correccion = "CORRECCION_GUIA_DROPSHIPPER" if rol == "DROPSHIPPER" else "CORRECCION_GUIA_PROVEEDOR"
    esperado_col = "ganancia_dropshipper_c" if rol == "DROPSHIPPER" else "ganancia_proveedor_c"
    tol = int(cfg["tolerancia_centavos"])

    o = ordenes.join(por_orden, how="left")
    df = pd.DataFrame(index=o.index)
    df["estatus"], df["tipo_envio"], df["fecha_entregado"] = o.estatus, o.tipo_envio, o.fecha_entregado
    df["lineas"] = o.lineas
    df["esperado_c"] = o[esperado_col]
    df["pagado_c"] = _col(o, concepto).fillna(0).astype("int64")
    df["corregido_c"] = (-_col(o, correccion).fillna(0)).astype("int64")
    df["neto_c"] = df.pagado_c - df.corregido_c
    df["n_pagos"] = _col(o, f"n_{concepto}").fillna(0).astype(int)
    df["fecha_pago"] = _col(o, f"f_{concepto}", pd.NaT)

    envios = [n.texto(e) for e in cfg["paga_en"][rol]["tipos_envio"]]
    debe_pagar = df.estatus.isin([n.texto(e) for e in cfg["paga_en"][rol]["estatus"]]) & df.tipo_envio.isin(envios)
    pagos_esperados = 1 if cfg["un_pago_por"][rol] == "ORDEN" else df.lineas
    ventana = pd.Timedelta(int(cfg["ventana_dias"]), unit="D")

    dif = df.neto_c - df.esperado_c
    cond = [
        debe_pagar & (df.n_pagos == 0) & (df.fecha_entregado >= (corte_wallet.normalize() - ventana)),
        debe_pagar & (df.n_pagos == 0),
        debe_pagar & (df.corregido_c > 0) & (df.neto_c.abs() <= tol),
        debe_pagar & (df.esperado_c == 0),
        debe_pagar & (dif.abs() <= tol),
        debe_pagar & (df.n_pagos > pagos_esperados) & (dif > tol),
        debe_pagar,
        ~debe_pagar & (df.n_pagos == 0),
        ~debe_pagar & (df.fecha_pago > corte_ordenes),
        ~debe_pagar & (df.neto_c.abs() <= tol),
    ]
    estados = [
        "EN_VENTANA",
        "SIN_PAGO",
        "REVERSADA",
        "PAGADA_SIN_VALIDAR",
        "PAGADA",
        "DUPLICADA",
        "DIFERENCIA_VALOR",
        "NO_APLICA",
        "PAGO_POSTERIOR_AL_REPORTE",
        "REVERSADA",
    ]
    df["estado"] = np.select(cond, estados, default="PAGO_SIN_ENTREGA")
    df["monto_en_juego_c"] = np.select(
        [df.estado.isin(["SIN_PAGO", "EN_VENTANA"]), df.estado.isin(["DIFERENCIA_VALOR", "DUPLICADA"]), df.estado == "PAGO_SIN_ENTREGA"],
        [df.esperado_c, dif.abs(), df.neto_c],
        default=0,
    ).astype("int64")
    df["gravedad"] = df.estado.map(GRAVEDAD).fillna("OK")
    return df


# ------------------------------------------------------- T2 orden sin recaudo (DS)


def orden_sin_recaudo(ordenes: pd.DataFrame, por_orden: pd.DataFrame, params: dict):
    cfg = params["orden_sin_recaudo"]
    tol = int(params["ganancia"]["tolerancia_centavos"])
    o = ordenes[ordenes.tipo_envio == "SIN RECAUDO"].join(por_orden, how="left")
    df = pd.DataFrame(index=o.index)
    df["estatus"] = o.estatus
    df["cobro_esperado_c"] = o.precio_proveedor_x_cantidad_c + o.precio_flete_c
    df["cobrado_c"] = (-_col(o, "COBRO_NUEVA_ORDEN").fillna(0)).astype("int64")
    df["n_cobros"] = _col(o, "n_COBRO_NUEVA_ORDEN").fillna(0).astype(int)
    df["reembolsado_c"] = _col(o, "REEMBOLSO_CAMBIO_ESTATUS").fillna(0).astype("int64")

    regla = {n.texto(k): v for k, v in cfg["reembolso_por_estatus"].items()}
    base_reembolso = {"TOTAL": df.cobrado_c, "PRODUCTO": o.precio_proveedor_x_cantidad_c}
    esperado = pd.Series(0, index=df.index, dtype="int64")
    for est, tipo in regla.items():
        m = df.estatus == est
        esperado[m] = base_reembolso[tipo][m]
    df["reembolso_esperado_c"] = esperado

    cond_cobro = [
        df.n_cobros == 0,
        df.n_cobros > 1,
        (df.cobrado_c - df.cobro_esperado_c).abs() <= tol,
    ]
    df["estado_cobro"] = np.select(cond_cobro, ["SIN_COBRO", "COBRO_DUPLICADO", "COBRO_CORRECTO"], default="DIFERENCIA_COBRO")
    d = df.reembolsado_c - df.reembolso_esperado_c
    cond_re = [
        (df.reembolso_esperado_c == 0) & (df.reembolsado_c == 0),
        (df.reembolso_esperado_c == 0) & (df.reembolsado_c > 0),
        d.abs() <= tol,
        df.reembolsado_c == 0,
    ]
    df["estado_reembolso"] = np.select(
        cond_re, ["NO_APLICA", "REEMBOLSO_NO_ESPERADO", "REEMBOLSADO", "SIN_REEMBOLSO"], default="REEMBOLSO_PARCIAL"
    )
    df["monto_en_juego_c"] = np.where(
        df.estado_reembolso.isin(["SIN_REEMBOLSO", "REEMBOLSO_PARCIAL"]), -d, 0
    ) + np.where(df.estado_cobro == "DIFERENCIA_COBRO", (df.cobrado_c - df.cobro_esperado_c).abs(), 0)
    df["gravedad"] = [
        max((GRAVEDAD.get(a, "OK"), GRAVEDAD.get(b, "OK")), key=["OK", "INFORMATIVO", "MEDIO", "CRITICO"].index)
        for a, b in zip(df.estado_cobro, df.estado_reembolso)
    ]
    return df


# ------------------------------------------------- T3 devolución con recaudo (DS)


def devolucion_con_recaudo(ordenes: pd.DataFrame, por_orden: pd.DataFrame, params: dict, corte_wallet):
    cfg = params["devolucion_con_recaudo"]
    tol = int(params["ganancia"]["tolerancia_centavos"])
    tabla = {n.texto(k): v for k, v in cfg["cobro_por_transportadora"].items()}
    estatus_dev = [n.texto(e) for e in cfg["estatus_devolucion"]]
    o = ordenes[ordenes.tipo_envio == "CON RECAUDO"].join(por_orden, how="left")
    cobro = -(_col(o, "COBRO_DEVOLUCION").fillna(0) + _col(o, "COBRO_FLETE_INICIAL").fillna(0))
    n_cobros = _col(o, "n_COBRO_DEVOLUCION").fillna(0) + _col(o, "n_COBRO_FLETE_INICIAL").fillna(0)
    es_dev = o.estatus.isin(estatus_dev)
    o = o[es_dev | (n_cobros > 0)]
    df = pd.DataFrame(index=o.index)
    df["estatus"], df["transportadora"], df["fecha_devolucion"] = o.estatus, o.transportadora, o.fecha_devolucion
    df["cobrado_c"] = cobro[o.index].astype("int64")
    df["n_cobros"] = n_cobros[o.index].astype(int)

    # El cobro de devolución es el flete sin la comisión de recaudo (en una devolución no se recauda):
    # esperado = PRECIO FLETE − (comision_pct × VALOR DE COMPRA + comision_fija). null = comisión por confirmar.
    def esperado(fila):
        t = tabla.get(fila.transportadora)
        if not t or t.get("comision_pct") is None:
            return pd.NA
        pct = Decimal(str(t["comision_pct"]))
        variable = (pct * int(o.at[fila.Index, "valor_compra_c"])).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        comision = int(variable) + int(t.get("comision_fija") or 0) * 100
        return int(o.at[fila.Index, "precio_flete_c"]) - comision

    df["precio_flete_c"] = o.precio_flete_c.astype("int64")
    df["cobro_esperado_c"] = pd.array([esperado(f) for f in df.itertuples()], dtype="Int64")
    ventana = pd.Timedelta(int(cfg["ventana_dias"]), unit="D")
    es_dev = df.estatus.isin(estatus_dev)
    sin_tarifa = df.cobro_esperado_c.isna()
    dif = (df.cobrado_c - df.cobro_esperado_c.fillna(0)).abs()
    cond = [
        ~es_dev,
        es_dev & (df.n_cobros == 0) & (df.fecha_devolucion >= corte_wallet.normalize() - ventana),
        es_dev & (df.n_cobros == 0),
        df.n_cobros > 1,
        df.cobrado_c > df.precio_flete_c + tol,
        sin_tarifa,
        dif <= tol,
    ]
    df["estado"] = np.select(
        cond,
        ["COBRO_ANTICIPADO", "EN_VENTANA", "SIN_COBRO", "DUPLICADO", "COBRO_MAYOR_AL_FLETE", "COBRADO_SIN_TARIFA", "COBRADO"],
        default="DIFERENCIA_TARIFA",
    )
    df["monto_en_juego_c"] = np.select(
        [df.estado == "DIFERENCIA_TARIFA", df.estado == "DUPLICADO", df.estado == "COBRO_MAYOR_AL_FLETE"],
        [dif, df.cobrado_c / 2, df.cobrado_c - df.precio_flete_c],
        0,
    ).astype("int64")
    df["gravedad"] = df.estado.map(GRAVEDAD).fillna("OK")
    return df


# ---------------------------------------------------------- T4 fulfillment (PROV)


def fulfillment_proveedor(ordenes: pd.DataFrame, por_orden: pd.DataFrame, params: dict, tarifas_ff: dict, corte_wallet, corte_ordenes):
    cfg = params["fulfillment_proveedor"]
    tol = int(params["ganancia"]["tolerancia_centavos"])
    tarifas = {n.texto(k): v for k, v in tarifas_ff.items()}
    o = ordenes.join(por_orden, how="left")
    df = pd.DataFrame(index=o.index)
    df["estatus"], df["tipo_envio"], df["bodega"], df["fecha_guia"] = o.estatus, o.tipo_envio, o.bodega, o.fecha_guia
    df["lineas"] = o.lineas
    df["cobrado_c"] = (-_col(o, "COBRO_FULFILLMENT").fillna(0)).astype("int64")
    df["reversado_c"] = _col(o, "REVERSO_COBRO_FF").fillna(0).astype("int64")
    df["neto_c"] = df.cobrado_c - df.reversado_c
    df["n_cobros"] = _col(o, "n_COBRO_FULFILLMENT").fillna(0).astype(int)
    df["fecha_cobro"] = _col(o, "f_COBRO_FULFILLMENT", pd.NaT)
    df["tarifa_c"] = pd.array([None if tarifas.get(b) is None else int(tarifas[b]) * 100 for b in df.bodega], dtype="Int64")

    # Cancelada nunca cobra. Los estados previos a la guía solo cuentan si el reporte no trae fecha de guía.
    no_cobra = [n.texto(e) for e in cfg["estatus_no_cobra"]]
    sin_guia = df.estatus.isin(no_cobra) | (df.estatus.isin([n.texto(e) for e in cfg["estatus_sin_guia"]]) & df.fecha_guia.isna())
    cobra = (
        df.bodega.isin(tarifas.keys())
        & df.tipo_envio.isin([n.texto(e) for e in cfg["tipos_envio_que_cobran"]])
        & ~sin_guia
    )
    ventana = pd.Timedelta(int(cfg["ventana_dias"]), unit="D")
    tarifa = df.tarifa_c.fillna(0).astype("int64")
    dif = df.neto_c - tarifa
    cond = [
        ~cobra & (df.cobrado_c == 0),
        ~cobra & (df.neto_c.abs() <= tol),
        ~cobra & (df.fecha_cobro > corte_ordenes),
        ~cobra,
        (df.cobrado_c > 0) & (df.neto_c.abs() <= tol),
        (df.cobrado_c == 0) & (df.fecha_guia >= corte_wallet.normalize() - ventana),
        df.cobrado_c == 0,
        df.tarifa_c.isna(),
        dif.abs() <= tol,
        (dif > tol) & ((dif - tarifa).abs() <= tol),
    ]
    estados = [
        "NO_APLICA",
        "REVERSADO",
        "COBRO_POSTERIOR_AL_REPORTE",
        "COBRO_NO_CORRESPONDE",
        "REVERSADO",
        "EN_VENTANA",
        "SIN_COBRO",
        "COBRADO_SIN_TARIFA",
        "COBRADO",
        "DUPLICADO",
    ]
    df["estado"] = np.select(cond, estados, default="DIFERENCIA_TARIFA")
    df["monto_en_juego_c"] = np.select(
        [df.estado.isin(["DUPLICADO", "DIFERENCIA_TARIFA"]), df.estado == "COBRO_NO_CORRESPONDE"], [dif.abs(), df.neto_c], 0
    ).astype("int64")
    df["gravedad"] = df.estado.map(GRAVEDAD).fillna("OK")
    return df


# ------------------------------------------------------------ fuera del reporte


def fuera_del_reporte(mov: pd.DataFrame, ordenes: pd.DataFrame, conceptos_de_orden: list[str], ids_reporte: pd.Series) -> pd.DataFrame:
    """Movimientos de órdenes que no son de la tienda en el reporte. Un movimiento por fila, con el motivo.

    ORDEN_ANTERIOR_AL_REPORTE   ID menor que el primero del reporte (órdenes de meses anteriores: pedir ese reporte).
    ORDEN_POSTERIOR_AL_REPORTE  ID mayor que el último del reporte (se crearon después de descargarlo).
    ORDEN_DE_OTRA_TIENDA        La orden está en el reporte pero la línea no es de esta tienda: revisar.
    NO_ENCONTRADA               ID dentro del rango pero no está en el reporte: revisar.

    Gravedad: OTRA_TIENDA y NO_ENCONTRADA = MEDIO; ANTERIOR = INFORMATIVO; POSTERIOR = OK (se valida con el
    reporte siguiente, no es hallazgo; decisión 30-sep).
    """
    m = mov[mov.orden_id.notna() & mov.concepto.isin(conceptos_de_orden) & ~mov.orden_id.isin(ordenes.index)].copy()
    ids = set(ids_reporte.dropna())
    num = pd.to_numeric(ids_reporte, errors="coerce")
    minimo, maximo = num.min(), num.max()
    oid = pd.to_numeric(m.orden_id, errors="coerce")
    m["motivo"] = np.select(
        [m.orden_id.isin(ids), oid < minimo, oid > maximo],
        ["ORDEN_DE_OTRA_TIENDA", "ORDEN_ANTERIOR_AL_REPORTE", "ORDEN_POSTERIOR_AL_REPORTE"],
        default="NO_ENCONTRADA",
    )
    m["gravedad"] = np.select(
        [m.motivo.isin(["ORDEN_DE_OTRA_TIENDA", "NO_ENCONTRADA"]), m.motivo == "ORDEN_POSTERIOR_AL_REPORTE"],
        ["MEDIO", "OK"],
        default="INFORMATIVO",
    )
    return m[["mov_id", "fecha", "concepto", "orden_id", "neto_c", "motivo", "gravedad", "descripcion"]]
