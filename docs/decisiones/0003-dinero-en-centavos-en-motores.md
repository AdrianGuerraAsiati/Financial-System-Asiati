# 0003 — Dinero en centavos enteros dentro de los motores

- Fecha: 2026-09-28
- Decidió: Juan Felipe Parra
- Estado: Aceptada

## Contexto
CLAUDE.md y la SPEC piden `NUMERIC(18,2)` en base de datos y `Decimal` en Python.
El motor de la wallet Wiilog (`app/motores/conciliacion_wallets/wiilog/`) es Python
puro sobre DataFrames de pandas, donde `Decimal` no es vectorizable y obliga a
columnas `object`. El motor trabaja en centavos enteros (`int`) a propósito.

## Decisión
Dentro de un motor, el dinero se opera en centavos enteros (`int64`). El núcleo
guarda `NUMERIC(18,2)` y convierte centavos a `Decimal` al guardar. Nunca float.

## Consecuencias
- Las columnas de dinero del motor terminan en `_c` y son enteras.
- La conversión a `Decimal` y a texto decimal ("7300000.00") ocurre en la frontera
  motor → núcleo, y en los resultados que el motor expone en JSON.
- La regla "nunca float" sigue igual: un monto nunca se opera como float.
