# 0006 — Wallets de tienda por rol, devolución = flete sin comisión de recaudo, y conciliación entre wallets

- Fecha: 2026-09-29
- Decidió: Juan Felipe Parra
- Estado: Aceptada

## Contexto
`PROMPT_MAESTRO.md` (V4) se escribió con los archivos de julio de 2026, antes de ver las
wallets de septiembre. Al correr las reglas sobre las cuatro wallets reales de septiembre
(Menpros, Proveeduría ASIATI, Recompra Menpros y pagos@asiati), cuatro puntos del prompt
maestro no cuadran con lo que muestran los datos. El detalle y las cifras están en
`docs/motores/conciliacion_wallets/WALLETS_TIENDAS_Y_PAGOS.md` §6 y §9.

## Decisión
Las wallets de Dropi se modelan por tipo y rol: TIENDA (con rol DROPSHIPPER o PROVEEDOR) y
SOLO_PAGOS. El cobro de una devolución con recaudo es el mismo flete, sin la comisión de
recaudo, porque en una devolución no se recauda plata (regla T3). La
conciliación entre wallets (mismo ID de orden en las dos wallets, y traslados emparejados) se
construye desde ya.

Las cuatro correcciones al prompt maestro:

1. **§4, wallet ASIATI.** El prompt decía que "solo recibe transferencias, sin reglas". La
   Proveeduría ASIATI es un **proveedor**: recibe ganancia por línea y paga el fulfillment a
   Wiilog (8.797 órdenes). La que solo recibe pagos es pagos@asiati.
   → Proveeduría = TIENDA con rol PROVEEDOR; pagos@ = SOLO_PAGOS.
2. **§7, concepto de fulfillment.** "SALIDA POR NUEVA ORDEN" no es el fulfillment: es el cobro
   de producto + flete de una orden **sin recaudo** (444 de 444 cuadran así). El fulfillment es
   "SALIDA POR FULFILLMENT" y lo paga el proveedor, no el dropshipper (Menpros tiene 0 cobros de FF).
   → C2 pasa a T4 (solo rol PROVEEDOR); nueva regla T2 para órdenes sin recaudo.
3. **§5.3, ventana de gracia.** El prompt fijaba 15 días. En septiembre el 100 % de las ganancias
   se pagó 1 día después de la entrega, en las dos tiendas.
   → Ventana de 2 días. Con 15, dos semanas de pagos faltantes quedarían escondidas como EN_VENTANA.
4. **§4, conciliación entre wallets.** El prompt decía no construirla todavía. El cruce de FF
   Proveeduría ↔ Wiilog explicó los 12 "cobros de 5.000" de Wiilog y encontró FF pagado en
   órdenes de otro proveedor. Es barato: el mismo ID de orden está en las dos wallets.
   → Se construye ya (cruce por orden y traslados emparejados).

Se conserva del prompt maestro: agrupar por orden, comparar contra `GANANCIA TOTAL DE DROPSHIPPER`,
sin recaudo fuera del universo de ganancia y C0 como freno.

## Consecuencias
- Nuevo código en `app/motores/conciliacion_wallets/tiendas/`, `pagos/` y `catalogo.py`, con
  parámetros en `parametros_wallet_tienda.json` y `parametros_wallet_pagos.json`.
- `PROMPT_MAESTRO.md` §4, §5.3 y §7 llevan una nota que remite a `WALLETS_TIENDAS_Y_PAGOS.md`;
  el texto original se conserva.
- No cambia el núcleo, las migraciones ni los endpoints. Conectar estas wallets a la base y a la
  API queda para otra tarea con el dueño del núcleo.
- La línea base de septiembre (`WALLETS_TIENDAS_Y_PAGOS.md` §6) es la regresión vigente de estas
  wallets. Si una cifra cambia, el PR tiene que explicar por qué.
