# Motor conciliacion_wallets — reglas para trabajar en esta carpeta

> **Alcance.** Las wallets de tienda (TIENDA) y de pagos (SOLO_PAGOS) tienen sus reglas en
> `tiendas/CLAUDE.md`, `pagos/CLAUDE.md` y `docs/motores/conciliacion_wallets/WALLETS_TIENDAS_Y_PAGOS.md`.
> La wallet Wiilog tiene las suyas en `wiilog/CLAUDE.md` y
> `docs/motores/conciliacion_wallets/WALLET_WIILOG.md`. La conciliación entre wallets ya se
> construye (decisión 0006). Lo que sigue en este archivo (línea base de julio, ventana de
> 15 días, reglas C0 a C6) es histórico del PROMPT_MAESTRO y no manda sobre esos documentos.

La especificación completa está en `docs/motores/conciliacion_wallets/PROMPT_MAESTRO.md`.
Trabaja fase por fase y para al final de cada una.

## Lo que este motor NO construye
Identidad, roles, períodos, cargas, hash, movimientos, categorización en 7
dimensiones, catálogo de reglas, ciclo de vida de hallazgos, parámetros
versionados, auditoría, export, Docker, CI. Eso es del núcleo.

## Las seis correcciones (nunca volver a la versión anterior)
1. El wallet paga ganancia: comparar contra `GANANCIA TOTAL DE DROPSHIPPER`, no contra el valor de compra.
2. Sin recaudo es una exclusión, no un hallazgo. Se cuenta aparte y no llega a la bandeja.
3. El pago llega con rezago: `ventana_gracia_dias` (arranca en 15). Dentro = `EN_VENTANA`, fuera = `SIN_PAGO`.
4. Agrupar por orden antes de cruzar. La base trae una fila por línea de producto.
5. La referencia es una pista: cascada ID → guía → dígitos → monto+fecha → sin match.
   Del nivel 3 en adelante va a revisión humana y nunca se cierra solo. Guardar siempre el nivel.
6. Validar el archivo antes de conciliar (C0): saldo final = inicial + entradas − salidas (tolerancia 1 peso).

## Diseño
- `rules/` es Python puro: recibe DataFrames y un dict de parámetros, devuelve resultados.
  Sin FastAPI, sin SQLAlchemy, sin base de datos.
- Una sola implementación para las tres wallets. Lo que cambia entre wallets vive en parámetros.
- La wallet ASIATI no tiene reglas de cruce: `ejecutar()` devuelve lista vacía y eso es correcto.
- No construir todavía la conciliación entre wallets; solo dejar el modelo preparado.

## Bloqueantes que no se adivinan
- Catálogo real de conceptos de las tres wallets (sale de la FASE 0).
- Regla de flete para C3: porcentaje, valor fijo o tabla por transportadora.
- Cómo Wiilog cobra el fulfillment por guía.
Si una tarea depende de alguno, deja `TODO(negocio)` y para.

## Línea base
La prueba de regresión usa los archivos de julio 2026 en `fixtures/` (fuera de git)
y se compara por estado y con montos, no solo con conteos.
