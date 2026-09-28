"""Regla FF: todo fulfillment generado desde una bodega Wiilog tiene que estar cobrado.

Momento del cobro
  CON RECAUDO -> cuando se genera la guía (FECHA GENERACION DE GUIA)
  SIN RECAUDO -> cuando la orden cierra (ENTREGADO o DEVOLUCION)

Estados por orden
  COBRADO             una entrada neta, tarifa correcta o por confirmar
  DUPLICADO           dos o más entradas para la misma orden          [hallazgo · medio]
  DIFERENCIA_TARIFA   cobrado con un valor distinto a la tarifa       [hallazgo · medio]
  NO_COBRADO          debía cobrarse y no hay entrada                 [hallazgo · crítico]
  EN_VENTANA          debía cobrarse hace menos de la ventana de gracia
  PENDIENTE_CIERRE    sin recaudo que todavía no cierra
  REVERSADO           cobrado y reversado por Dropi (orden rechazada)
  COBRADO_NO_CORRESPONDE  cobro en una bodega que no cobra FF (p. ej. Bucaramanga)  [hallazgo · medio]
  NO_APLICA           bodega externa o sin FF, sin guía, o rechazada sin cobro
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import normalizar as n

CONCEPTOS_FF = ["FF_GUIA_GENERADA", "FF_CIERRE", "FF_OTRO_USUARIO", "FF_CORRECCION"]
SEVERIDAD = {"NO_COBRADO": "critico", "DUPLICADO": "medio", "DIFERENCIA_TARIFA": "medio", "COBRADO_NO_CORRESPONDE": "medio"}


def _pagos_por_orden(wallet: pd.DataFrame) -> pd.DataFrame:
    ff = wallet[wallet.concepto.isin(CONCEPTOS_FF) & wallet.orden_id.notna()]
    entradas = ff[ff.concepto != "FF_CORRECCION"]
    agg = pd.DataFrame(
        {
            "ff_neto_c": ff.groupby("orden_id")["neto_c"].sum(),
            "ff_entradas": entradas.groupby("orden_id").size(),
            "ff_correcciones": ff[ff.concepto == "FF_CORRECCION"].groupby("orden_id").size(),
            "ff_conceptos": entradas.groupby("orden_id")["concepto"].agg(lambda s: "/".join(sorted(set(s)))),
            "ff_primer_cobro": entradas.groupby("orden_id")["fecha"].min(),
            "ff_movimientos": ff.groupby("orden_id")["mov_id"].agg(lambda s: ",".join(map(str, s))),
        }
    )
    return agg.fillna({"ff_neto_c": 0, "ff_entradas": 0, "ff_correcciones": 0}).astype(
        {"ff_neto_c": "int64", "ff_entradas": "int64", "ff_correcciones": "int64"}
    )


def conciliar(ordenes: pd.DataFrame, wallet: pd.DataFrame, params: dict, fecha_corte: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (resultado por orden del reporte, cobros de FF sin orden en el reporte)."""
    cfg = params["fulfillment"]
    prefijo = n.texto(cfg["bodegas_que_cobran_prefijo"])
    sin_ff = {n.texto(b) for b in cfg.get("bodegas_sin_fulfillment", [])}
    cobra_en_devolucion = bool(cfg.get("sin_recaudo_cobra_en_devolucion", True))
    tarifas = {n.texto(k): v for k, v in cfg["tarifas_por_bodega"].items()}
    general_c = n.centavos(cfg["tarifa_general"])
    tol = int(cfg["tolerancia_centavos"])
    cierre = set(cfg["estados_cierre"])
    reversa = set(cfg["estados_reversa"])
    limite = (fecha_corte.normalize() - pd.Timedelta(int(cfg["ventana_gracia_dias"]), unit="D"))

    pagos = _pagos_por_orden(wallet)
    r = ordenes.join(pagos, how="left")
    r[["ff_neto_c", "ff_entradas", "ff_correcciones"]] = r[["ff_neto_c", "ff_entradas", "ff_correcciones"]].fillna(0).astype("int64")

    r["bodega_wiilog"] = r["bodega"].str.startswith(prefijo)
    # Bodega que cobra FF: es de Wiilog y no está en la lista de bodegas sin fulfillment.
    r["bodega_cobra_ff"] = r["bodega_wiilog"] & ~r["bodega"].isin(sin_ff)
    tarifa = r["bodega"].map(tarifas)
    r["tarifa_confirmada"] = tarifa.notna()
    r["tarifa_c"] = tarifa.map(lambda v: n.centavos(v) if pd.notna(v) else general_c)

    sin_recaudo = r["tipo_envio"] == "SIN RECAUDO"
    r["momento_cobro"] = np.where(sin_recaudo, "CIERRE", "GUIA_GENERADA")
    r["fecha_hecho"] = np.where(sin_recaudo, r["fecha_cierre"], r["fecha_guia"])
    r["fecha_hecho"] = pd.to_datetime(r["fecha_hecho"])
    cierre_sr = cierre if cobra_en_devolucion else (cierre - {"DEVOLUCION"})
    cerrada = r["estatus"].isin(cierre_sr)
    debia = np.where(sin_recaudo, cerrada, r["fecha_guia"].notna())

    estado = np.full(len(r), "NO_APLICA", dtype=object)
    wi = r["bodega_cobra_ff"].to_numpy()
    wiilog_sin_ff = (r["bodega_wiilog"] & ~r["bodega_cobra_ff"]).to_numpy()
    rev = r["estatus"].isin(reversa).to_numpy()
    cobrado = (r["ff_neto_c"] > 0).to_numpy()
    tuvo_entrada = (r["ff_entradas"] > 0).to_numpy()
    duplicado = (r["ff_entradas"] >= 2).to_numpy() & cobrado
    difiere = (r["tarifa_confirmada"] & ((r["ff_neto_c"] - r["tarifa_c"]).abs() > tol)).to_numpy()
    en_ventana = (r["fecha_hecho"] >= limite).to_numpy()

    for i in range(len(r)):
        if wiilog_sin_ff[i]:
            estado[i] = "COBRADO_NO_CORRESPONDE" if cobrado[i] else "NO_APLICA"
        elif not wi[i]:
            estado[i] = "NO_APLICA"
        elif rev[i]:
            estado[i] = "REVERSADO" if tuvo_entrada[i] and not cobrado[i] else ("COBRADO" if cobrado[i] else "NO_APLICA")
        elif duplicado[i]:
            estado[i] = "DUPLICADO"
        elif cobrado[i]:
            estado[i] = "DIFERENCIA_TARIFA" if difiere[i] else "COBRADO"
        elif not debia[i]:
            estado[i] = "PENDIENTE_CIERRE" if sin_recaudo.iloc[i] and pd.notna(r["fecha_guia"].iloc[i]) else "NO_APLICA"
        elif en_ventana[i]:
            estado[i] = "EN_VENTANA"
        else:
            estado[i] = "NO_COBRADO"
    r["estado_ff"] = estado
    r["severidad"] = r["estado_ff"].map(SEVERIDAD).fillna("informativo")
    r["dias_desde_hecho"] = (fecha_corte.normalize() - r["fecha_hecho"]).dt.days
    # Monto en juego: lo que falta cobrar, o lo cobrado de más.
    en_juego = np.select(
        [r.estado_ff == "NO_COBRADO", r.estado_ff == "DUPLICADO", r.estado_ff == "DIFERENCIA_TARIFA", r.estado_ff == "COBRADO_NO_CORRESPONDE"],
        [r.tarifa_c, r.ff_neto_c - r.tarifa_c, (r.ff_neto_c - r.tarifa_c).abs(), r.ff_neto_c],
        0,
    )
    r["monto_en_juego_c"] = en_juego.astype("int64")

    # Lado wallet: cobros de FF de órdenes que no están en el reporte de órdenes.
    fuera = pagos[~pagos.index.isin(ordenes.index)].copy()
    fuera["estado_ff"] = np.where(
        fuera["ff_conceptos"].fillna("").str.contains("FF_OTRO_USUARIO"), "FUERA_MARCA_BLANCA", "FUERA_DEL_REPORTE"
    )
    return r, fuera
