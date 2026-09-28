"""Regla FLETE: 1.000 pesos por cada guía nativa de marca blanca que cierra (entregada o devuelta).

No se cobra en guías de transportadora WIILOG. Saber si una guía es nativa exige la columna
MARCA BLANCA, que solo trae el reporte que comparte el KAM de Dropi. Sin esa columna, las guías
cerradas sin cobro quedan SIN_VERIFICAR, nunca NO_COBRADO.

Estados por orden
  COBRADO                 una comisión por guía cerrada
  DUPLICADO               dos o más comisiones en la misma orden            [hallazgo · medio]
  DIFERENCIA_VALOR        cobrada con un valor distinto a la comisión       [hallazgo · medio]
  COBRADO_NO_CORRESPONDE  cobrada en transportadora WIILOG o guía no nativa [hallazgo · medio]
  NO_COBRADO              guía nativa cerrada sin comisión                  [hallazgo · crítico]
  SIN_VERIFICAR           cerrada sin comisión y sin columna MARCA BLANCA
  PENDIENTE_CIERRE        la guía no ha cerrado
  NO_APLICA               transportadora WIILOG o guía no nativa, sin cobro
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import normalizar as n

SEVERIDAD = {"NO_COBRADO": "critico", "DUPLICADO": "medio", "DIFERENCIA_VALOR": "medio", "COBRADO_NO_CORRESPONDE": "medio"}
_SI = {"SI", "S", "TRUE", "VERDADERO", "1", "X", "MARCA BLANCA"}


def conciliar(ordenes: pd.DataFrame, wallet: pd.DataFrame, params: dict, fecha_corte: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = params["flete_marca_blanca"]
    comision_c = n.centavos(cfg["comision_por_guia"])
    cierre = set(cfg["estados_cobro"])
    excluidas = {n.texto(t) for t in cfg["transportadoras_excluidas"]}

    fl = wallet[(wallet.concepto == "FLETE_MB") & wallet.orden_id.notna()]
    pagos = pd.DataFrame(
        {
            "flete_neto_c": fl.groupby("orden_id")["neto_c"].sum(),
            "flete_entradas": fl.groupby("orden_id").size(),
            "flete_movimientos": fl.groupby("orden_id")["mov_id"].agg(lambda s: ",".join(map(str, s))),
        }
    )
    r = ordenes.join(pagos, how="left")
    r[["flete_neto_c", "flete_entradas"]] = r[["flete_neto_c", "flete_entradas"]].fillna(0).astype("int64")

    hay_columna_mb = r["marca_blanca"].notna().any()
    nativa = r["marca_blanca"].isin(_SI) if hay_columna_mb else pd.Series(pd.NA, index=r.index)
    cerrada = r["estatus"].isin(cierre)
    excluida = r["transportadora"].isin(excluidas)
    cobrado = r["flete_neto_c"] > 0

    estado = []
    for i in range(len(r)):
        c, ex, pag, ent = bool(cerrada.iloc[i]), bool(excluida.iloc[i]), bool(cobrado.iloc[i]), int(r["flete_entradas"].iloc[i])
        nat = nativa.iloc[i]
        if pag and (ex or (hay_columna_mb and not bool(nat))):
            estado.append("COBRADO_NO_CORRESPONDE")
        elif ent >= 2:
            estado.append("DUPLICADO")
        elif pag:
            estado.append("COBRADO" if abs(int(r["flete_neto_c"].iloc[i]) - comision_c) <= 0 else "DIFERENCIA_VALOR")
        elif ex:
            estado.append("NO_APLICA")
        elif not c:
            estado.append("PENDIENTE_CIERRE" if pd.notna(r["fecha_guia"].iloc[i]) else "NO_APLICA")
        elif not hay_columna_mb:
            estado.append("SIN_VERIFICAR")
        elif nat:
            estado.append("NO_COBRADO")
        else:
            estado.append("NO_APLICA")
    r["estado_flete"] = estado
    r["severidad"] = r["estado_flete"].map(SEVERIDAD).fillna("informativo")
    r["monto_en_juego_c"] = np.select(
        [r.estado_flete == "NO_COBRADO", r.estado_flete.isin(["DUPLICADO", "DIFERENCIA_VALOR"]), r.estado_flete == "COBRADO_NO_CORRESPONDE"],
        [comision_c, (r.flete_neto_c - comision_c).abs(), r.flete_neto_c],
        0,
    ).astype("int64")

    fuera = pagos[~pagos.index.isin(ordenes.index)].copy()
    fuera["estado_flete"] = "FUERA_DEL_REPORTE"
    return r, fuera
