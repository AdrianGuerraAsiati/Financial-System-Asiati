# Wallet Wiilog — reglas para trabajar en esta carpeta

Especificación: docs/motores/conciliacion_wallets/WALLET_WIILOG.md
Parámetros:     docs/motores/conciliacion_wallets/parametros_wallet_wiilog.json

- Python puro: DataFrames y un dict de parámetros. Sin FastAPI, sin SQLAlchemy.
- Dinero en centavos enteros (int). Nunca float. El núcleo lo guarda como NUMERIC(18,2).
- El saldo se valida ordenando por ID del movimiento, nunca por fecha.
- Las órdenes se agrupan por ID antes de cruzar: el reporte trae una fila por línea.
- Texto normalizado (mayúsculas, sin tildes, espacios colapsados) antes de comparar.
  La bodega llega con tabulaciones ("WIILOG MEDELLÍN\t 2.0").
- Sin la columna MARCA BLANCA, la regla de flete deja SIN_VERIFICAR, nunca NO_COBRADO.
- Tarifas de FF por bodega en null = por confirmar. No inventes tarifas.
- La línea base de septiembre (WALLET_WIILOG.md §7) no se cambia sin explicar por qué en el PR.
- Los archivos reales van en fixtures/ y nunca se suben a git.
