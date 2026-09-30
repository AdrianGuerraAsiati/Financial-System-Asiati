"""Corre la conciliación de la wallet Wiilog desde la línea de comandos, sin base de datos.

    python -m app.motores.conciliacion_wallets.wiilog ORDENES.xlsx WALLET.xlsx 2026-09-01 2026-09-30
"""
import json
import sys
import pandas as pd

from .integracion import cargar_parametros_wiilog
from .motor import conciliar_wallet_wiilog


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__)
        return 2
    ordenes, wallet, desde, hasta = argv
    params = cargar_parametros_wiilog()
    r = conciliar_wallet_wiilog(pd.read_excel(ordenes), pd.read_excel(wallet), params, desde, hasta)
    for c in r.chequeos:
        print(f"{c.codigo}: {c.estado} · {c.mensaje}")
    if r.bloqueado:
        return 1
    print(json.dumps(r.resumen, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
