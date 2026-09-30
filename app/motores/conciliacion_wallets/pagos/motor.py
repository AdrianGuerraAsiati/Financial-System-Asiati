"""Punto de entrada del motor para wallets SOLO_PAGOS (no se cruzan contra órdenes). Python puro.

    r = conciliar_wallet_pagos(wallet_crudo, params, catalogo, wallet, periodo_inicio, periodo_fin)

Hace dos cosas: valida el saldo (C0) y categoriza cada movimiento con el catálogo, como un extracto
bancario. Lo que el catálogo marca requiere_revision queda para que el conciliador confirme con
observación. Las entradas de terceros externos son pagos de clientes: se identifican por el correo
(tercero); el cruce contra cartera se hará en el motor de cartera, no aquí.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .. import catalogo as cat
from ..wiilog import carga, movimientos
from ..wiilog import normalizar as n


@dataclass
class ResultadoPagos:
    bloqueado: bool
    chequeos: list
    wallet: dict = field(default_factory=dict)
    movimientos: pd.DataFrame | None = None
    resumen: dict = field(default_factory=dict)


def conciliar_wallet_pagos(wallet_crudo, params, catalogo, wallet, periodo_inicio, periodo_fin) -> ResultadoPagos:
    w = carga.leer_wallet(wallet_crudo, params)
    chequeos = movimientos.validar_integridad(w, periodo_inicio, periodo_fin)
    if any(c.estado == "BLOQUEADO" for c in chequeos):
        return ResultadoPagos(bloqueado=True, chequeos=chequeos, wallet=wallet)
    mov = cat.categorizar(w, catalogo, {**wallet, "wallets_propias": params.get("wallets_propias", []), "cuentas_destino_grupo": params.get("cuentas_destino_grupo", [])})
    # Entrada de un tercero externo = pago de cliente (solo se propone; se confirma contra cartera).
    ext = (mov.concepto == "TRANSFERENCIA_RECIBIDA") & (mov.ingreso_egreso != "TRASLADO")
    mov.loc[ext, "categoria"] = "PAGO DE CLIENTE POR WALLET"
    mov.loc[ext, "unidad_negocio"] = wallet.get("unidad_negocio_pagos")
    g = mov.groupby(["ingreso_egreso", "concepto"]).agg(n=("mov_id", "size"), c=("monto_c", "sum"))
    resumen = {
        "wallet": wallet["usuario_email"],
        "movimientos": {f"{a} · {b}": {"n": int(v.n), "monto": str(n.pesos(int(v.c)))} for (a, b), v in g.iterrows()},
        "por_revisar": int(mov.requiere_revision.sum()),
        "sin_concepto": int((mov.concepto == "SIN_CONCEPTO").sum()),
    }
    return ResultadoPagos(bloqueado=False, chequeos=chequeos, wallet=wallet, movimientos=mov, resumen=resumen)
