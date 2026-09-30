"""Categorización de movimientos con el catálogo de conceptos (común a todas las wallets Dropi).

    mov = categorizar(wallet, catalogo, wallet_params)

- `wallet` sale de wiilog.carga.leer_wallet (un movimiento por fila, centavos enteros, ordenado por ID).
- `catalogo` es docs/motores/conciliacion_wallets/catalogo_conceptos_wallets.json.
- La empresa sale de la wallet (wallet_params["empresa"]), nunca del concepto.
- requiere_revision = el sistema propone y el conciliador confirma, con observación obligatoria.

Python puro. Sin base de datos.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from .wiilog import normalizar as n

_CORREO = re.compile(r"([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})")
_MOTIVO_RET_ADMIN = re.compile(r"^RET\. ADMIN:\s*(.+)$")


def _tercero(concepto: str, desc_norm: str) -> str | None:
    """NA salvo transferencias, recargas a otro usuario y RET. ADMIN."""
    if m := _CORREO.search(desc_norm):
        return m.group(1).lower()
    if concepto.startswith("RET_ADMIN") and (m := _MOTIVO_RET_ADMIN.search(desc_norm)):
        return m.group(1).strip()
    return None


def clasificar_concepto(tipo: str, desc_norm: str, reglas: list[dict]) -> str:
    """La primera regla que empareja gana. Tipo y texto ya normalizados."""
    for r in reglas:
        if r["tipo"] != tipo:
            continue
        if desc_norm.startswith(n.texto(r["empieza_con"])) and n.texto(r.get("contiene") or "") in desc_norm:
            return r["codigo"]
    return "SIN_CONCEPTO"


def categorizar(wallet: pd.DataFrame, catalogo: dict, wallet_params: dict) -> pd.DataFrame:
    reglas = catalogo["conceptos"]
    por_codigo = {r["codigo"]: r for r in reglas}
    w = wallet.copy()
    w["concepto"] = [clasificar_concepto(t, d, reglas) for t, d in zip(w["tipo"], w["descripcion_norm"])]
    w["tercero"] = [_tercero(c, d) for c, d in zip(w["concepto"], w["descripcion_norm"])]

    def campo(nombre, defecto=None):
        return w["concepto"].map(lambda c: por_codigo.get(c, {}).get(nombre, defecto))

    w["ingreso_egreso"] = campo("ingreso_egreso", "PENDIENTE")
    w["unidad_negocio"] = campo("unidad_negocio")
    w["categoria"] = campo("categoria")
    w["empresa"] = wallet_params.get("empresa")  # null = por confirmar
    w["wallet"] = wallet_params["usuario_email"]
    w["modalidad"] = "WALLET"
    w["fijo_variable"] = "VARIABLE"
    w["requiere_revision"] = campo("requiere_revision", True).astype(bool) | (w["concepto"] == "SIN_CONCEPTO")

    # Transferencias entre wallets propias: no son ingreso ni gasto del grupo, son traslado intercompany.
    propias = {e.lower() for e in wallet_params.get("wallets_propias", [])}
    es_transfer = w["concepto"].isin(["TRANSFERENCIA_ENVIADA", "TRANSFERENCIA_RECIBIDA"])
    interna = es_transfer & w["tercero"].isin(propias)
    w.loc[interna, "ingreso_egreso"] = "TRASLADO"
    w.loc[interna, "unidad_negocio"] = "TRANSFER INTERCOMPANY"
    w.loc[interna, "categoria"] = "TRASLADO ENTRE WALLETS PROPIAS"
    w.loc[interna, "requiere_revision"] = False
    # Cuentas del grupo que son destino (no wallets conciliadas): el movimiento no es traslado automático;
    # el conciliador lo categoriza según para qué se envió.
    destino = {e.lower() for e in wallet_params.get("cuentas_destino_grupo", [])}
    a_destino = es_transfer & w["tercero"].isin(destino)
    w.loc[a_destino, ["unidad_negocio", "categoria"]] = [None, None]
    w.loc[a_destino, "requiere_revision"] = True
    w["tipo_tercero"] = np.select(
        [interna, a_destino, w["tercero"].notna()], ["WALLET_PROPIA", "CUENTA_DESTINO_GRUPO", "EXTERNO"], default=None
    )
    w["observacion"] = ""
    w.loc[a_destino, "observacion"] = "Cuenta destino del grupo: categorizar según para qué se envió."
    w["cruce_id"] = pd.NA
    return w


def cruzar_entre_wallets(movs: dict[str, pd.DataFrame], ventana_min: int = 10) -> dict[str, pd.DataFrame]:
    """Empareja SALIDA POR TRANSFERENCIA (A→B) con ENTRADA POR TRANSFERENCIA (B desde A).

    Mismo monto, dentro de la ventana. Solo entre wallets cargadas en la misma conciliación.
    Lo que queda sin pareja y es entre wallets propias se marca para revisión.
    """
    ventana = pd.Timedelta(ventana_min, unit="min")
    out = {k: v.copy() for k, v in movs.items()}
    k = 0
    for a, wa in out.items():
        salidas = wa[(wa.concepto == "TRANSFERENCIA_ENVIADA") & wa.tercero.isin(out.keys())]
        for i, s in salidas.iterrows():
            wb = out[s.tercero]
            cand = wb[
                (wb.concepto == "TRANSFERENCIA_RECIBIDA")
                & (wb.tercero == a)
                & (wb.monto_c == s.monto_c)
                & wb.cruce_id.isna()
                & ((wb.fecha - s.fecha).abs() <= ventana)
            ]
            if cand.empty:
                continue
            j = (cand.fecha - s.fecha).abs().idxmin()
            k += 1
            cid = f"INTERCO-{k:03d}"
            wa.at[i, "cruce_id"] = cid
            wb.at[j, "cruce_id"] = cid
    for nombre, w in out.items():
        solos = (w.ingreso_egreso == "TRASLADO") & w.cruce_id.isna() & w.tercero.isin(out.keys())
        w.loc[solos, "requiere_revision"] = True
        w.loc[solos, "observacion"] = "Traslado entre wallets propias sin contrapartida en la otra wallet."
    return out
