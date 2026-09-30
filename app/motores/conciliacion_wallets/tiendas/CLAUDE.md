# Wallets de tienda y de pagos — reglas para trabajar en estas carpetas

Especificación: docs/motores/conciliacion_wallets/WALLETS_TIENDAS_Y_PAGOS.md
Parámetros:     docs/motores/conciliacion_wallets/parametros_wallet_tienda.json y parametros_wallet_pagos.json
Catálogo:       docs/motores/conciliacion_wallets/catalogo_conceptos_wallets.json (común a todas las wallets)

- Python puro: DataFrames y dicts de parámetros. Sin FastAPI, sin SQLAlchemy.
- Dinero en centavos enteros (int). Nunca float.
- El saldo se valida ordenando por ID del movimiento, nunca por fecha.
- La empresa sale de la wallet (parámetros), nunca del concepto. null = por confirmar; no se inventa.
- Las líneas de órdenes se filtran por el rol de la tienda (EMAIL o PROVEEDOR EMAIL) y luego se agrupan por ID.
- Tarifas de FF: solo en parametros_wallet_wiilog.json. No se copian aquí.
- Comisión o tarifa en null = por confirmar: el cobro se acepta y queda *_SIN_TARIFA, nunca DIFERENCIA.
- Devolución con recaudo = PRECIO FLETE menos la comisión de recaudo; nunca puede ser mayor que el PRECIO FLETE.
- Transferencias a cuentas_destino_grupo no son traslado automático: el conciliador las categoriza.
- Un pago o cobro con fecha posterior al reporte de órdenes queda *_POSTERIOR_AL_REPORTE, no es hallazgo.
- La línea base de septiembre (WALLETS_TIENDAS_Y_PAGOS.md §6) no se cambia sin explicar por qué en el PR.
- Los archivos reales van en fixtures/ y nunca se suben a git.
