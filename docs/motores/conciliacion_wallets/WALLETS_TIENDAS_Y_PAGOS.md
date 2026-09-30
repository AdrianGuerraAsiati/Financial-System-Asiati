# Wallets de tienda y de pagos — especificación v1

Versión 2 · 29-sep-2026 (respuestas de Juan Felipe incorporadas) · Dueño de reglas: Juan Felipe Parra · Motor: `conciliacion_wallets`

Parámetros: `parametros_wallet_tienda.json`, `parametros_wallet_pagos.json`
Catálogo de conceptos (común a todas las wallets): `catalogo_conceptos_wallets.json`
Código de referencia: `app/motores/conciliacion_wallets/{catalogo.py, tiendas/, pagos/}`

## 1. Qué cubre

El motor de conciliación de wallets tiene tres tipos de wallet. Wiilog marca blanca ya está en `WALLET_WIILOG.md`.

| Tipo | Qué se hace | Wallets de septiembre |
|---|---|---|
| RECAUDADORA | Cruce contra órdenes (FF y flete marca blanca) | Wiilog marca blanca |
| TIENDA | Auditoría: ¿Dropi pagó y cobró lo que debía? Rol DROPSHIPPER o PROVEEDOR | Menpros y Recompra Menpros (DS, ORIGEN VITAL), Proveeduría ASIATI (PROV, TIENDAS ASIATI) |
| SOLO_PAGOS | Saldo (C0) + categorización, como un extracto bancario | Pagos Dropi · pagos@asiati.com.co (ASIATI) |

Empresa por wallet (29-sep): las de Wiilog = WIILOG; Pagos = ASIATI; tiendas = TIENDAS ASIATI, salvo Menpros y Recompra Menpros = ORIGEN VITAL.

Fuera de alcance por ahora: Belleza PRO, Patiño (tiendas sin conciliación), Dropicards, cartera.

## 2. Entradas

- Historial de la wallet (exportación de Dropi). Mismas columnas que la wallet de Wiilog.
- Reporte de órdenes de Dropi (el mismo del motor Wiilog). Una fila por línea de producto.
- Hora de descarga del reporte (va en el nombre del archivo, `ordenes_sept_20260928_144134` = 28-sep 14:41).
  Sin ella se usa el fin del día de `FECHA DE REPORTE`.

Las líneas de la tienda se filtran por su rol: DROPSHIPPER por la columna `EMAIL`, PROVEEDOR por `PROVEEDOR EMAIL`.
Después se agrupa por ID de orden.

## 3. Saldo y categorización (todas las wallets)

**C0.** Igual que Wiilog: el saldo se valida ordenando por ID del movimiento. Si no cuadra, no se concilia.

**Catálogo.** Cada movimiento recibe un concepto por el texto de Dropi (primera regla que empareja gana) y de ahí:
ingreso/egreso, unidad de negocio, categoría, requiere revisión. Tercero: el correo o el motivo del RET. ADMIN.

Cambios respecto a la tabla del flujo de caja anterior:

1. **La empresa sale de la wallet, no del concepto.** En la tabla, "SALIDA POR NUEVA ORDEN" tenía una empresa fija; pero la
   misma línea aparece en wallets de empresas distintas. Cada wallet declara su empresa en los parámetros (hoy null = por confirmar).
2. **Las filas en rojo (VARIABLE)** — cobro de flete por garantía, entrada por retiro admin, retiro de cartera negada — quedan con
   `requiere_revision`: el sistema propone y el conciliador confirma con observación obligatoria.
3. **Transferencias entre wallets propias** no son ingreso ni gasto: son TRASLADO y se emparejan entre las dos wallets.
4. **Textos nuevos** que no estaban en la tabla: corrección de guía como dropshipper/proveedor/referidos, cobro y reverso de
   fulfillment, dispersión y mantenimiento de tarjeta, RET. ADMIN por saldo negativo, cruces de marca blanca. Ver `origen` en el catálogo.

## 4. Reglas de tienda

Gravedad (las tiendas son del grupo): plata que Dropi le debe a la tienda = CRÍTICO; cobro de más = MEDIO; lo demás = INFORMATIVO.

### T1 · Ganancia (DROPSHIPPER y PROVEEDOR)

| | Dropshipper | Proveedor |
|---|---|---|
| Cuándo paga | Orden ENTREGADA **con recaudo** | Orden ENTREGADA, con o sin recaudo |
| Cuánto | `GANANCIA TOTAL DE DROPSHIPPER` | `GANANCIA TOTAL DE PROVEEDORES` (sus líneas) |
| Cuántos pagos | 1 por orden | 1 por línea |

Neto = pagos − correcciones de guía. Ventana: 2 días desde la entrega. Tolerancia: 1 peso.

Estados: PAGADA · PAGADA_SIN_VALIDAR (el reporte trae 0) · EN_VENTANA · SIN_PAGO (crítico) · DIFERENCIA_VALOR (crítico) ·
DUPLICADA · REVERSADA · PAGO_POSTERIOR_AL_REPORTE (pagó después de descargar el reporte) · PAGO_SIN_ENTREGA · NO_APLICA.

### T2 · Orden sin recaudo (DROPSHIPPER)

- Cobro al crear la orden = `PRECIO PROVEEDOR X CANTIDAD` + `PRECIO FLETE`, una vez.
- Reembolso: CANCELADO o RECHAZADO = todo lo cobrado; DEVOLUCION = solo el producto (el flete se pierde).
- Estados del cobro: COBRO_CORRECTO · DIFERENCIA_COBRO · COBRO_DUPLICADO · SIN_COBRO.
- Estados del reembolso: REEMBOLSADO · SIN_REEMBOLSO (crítico) · REEMBOLSO_PARCIAL (crítico) · REEMBOLSO_NO_ESPERADO · NO_APLICA.

### T3 · Devolución con recaudo (DROPSHIPPER)

Un solo cobro por devolución y es **el mismo flete, pero sin la comisión de recaudo** (en una devolución no se recauda plata).
El `PRECIO FLETE` del reporte trae esa comisión incluida, por eso no coincide a simple vista:

`cobro esperado = PRECIO FLETE − (comisión % × VALOR DE COMPRA + comisión fija)`

| Transportadora | Concepto en la wallet | Comisión de recaudo | Evidencia septiembre |
|---|---|---|---|
| Interrapidísimo | Cobro de flete inicial | 0 (cobra el flete completo) | 151 de 151 |
| Wiilog | Cobro de flete inicial | 3 % | 76 de 76 |
| Envía | Cobro de devolución | 4,5 % + 1.000 | 314 de 322 |
| Coordinadora, TCC | Cobro de devolución | **por confirmar** | 11 y 3 casos, sin patrón |

Ejemplo Envía: flete 21.455,50 en una orden de 129.900 → comisión 4,5 % × 129.900 + 1.000 = 6.845,50 → cobro 14.610.

Regla que aplica siempre, con o sin comisión conocida: **el cobro nunca puede ser mayor que el PRECIO FLETE** (COBRO_MAYOR_AL_FLETE).
La columna `COSTO DEVOLUCION FLETE` del reporte no coincide con lo cobrado; no se usa.

Estados: COBRADO · COBRADO_SIN_TARIFA (comisión por confirmar) · DIFERENCIA_TARIFA · COBRO_MAYOR_AL_FLETE · DUPLICADO · SIN_COBRO ·
EN_VENTANA · COBRO_ANTICIPADO (cobró antes de que la orden quedara en devolución).

### T4 · Fulfillment al proveedor (PROVEEDOR)

- Tarifa de la bodega **una vez por orden**; Dropi la reparte entre líneas (2 líneas = 2 cobros de 1.250).
- Tarifas: las de `parametros_wallet_wiilog.json` (una sola fuente de verdad).
- Solo con recaudo. Cancelada, o sin guía (pendiente, en procesamiento, etc. sin fecha de guía), no cobra.
- Estados: COBRADO · DUPLICADO (2 × tarifa) · DIFERENCIA_TARIFA · COBRADO_SIN_TARIFA · COBRO_NO_CORRESPONDE ·
  COBRO_POSTERIOR_AL_REPORTE · SIN_COBRO · EN_VENTANA · REVERSADO · NO_APLICA.

### Fuera del reporte

Movimientos de órdenes que no son de la tienda en el reporte, con motivo:
ORDEN_ANTERIOR_AL_REPORTE (meses anteriores) · ORDEN_POSTERIOR_AL_REPORTE · ORDEN_DE_OTRA_TIENDA (revisar) · NO_ENCONTRADA (revisar).

## 5. Wallets de solo pagos

**Terceros.** Cada transferencia lleva `tipo_tercero`: WALLET_PROPIA (wallet conciliada del grupo: TRASLADO y se empareja),
CUENTA_DESTINO_GRUPO (teampekop, mixmarketc, kuaimai903: son del grupo pero no se concilian; el conciliador categoriza el
movimiento según para qué se envió) o EXTERNO.

C0 + catálogo. Una transferencia recibida de un tercero externo se propone como "PAGO DE CLIENTE POR WALLET" con el correo
como tercero. El cruce contra facturas es del motor de cartera, no de este.

## 6. Línea base de septiembre (regresión)

Reporte de órdenes 28-sep 14:41; wallets descargadas 29-sep. Si una cifra cambia, el PR explica por qué.

| Wallet | Saldo inicial | Entradas | Salidas | Saldo final | Movimientos |
|---|---:|---:|---:|---:|---:|
| Menpros | 33.327.591,35 | 349.528.529,28 | 309.063.745,47 | 73.792.375,17 | 8.089 |
| Proveeduría ASIATI | 0,88 | 349.291.276,25 | 349.421.275,86 | −129.998,73 | 17.545 |
| Recompra Menpros (Comercial Contact Center) | 4.542.732,16 | 0 | 4.542.390,00 | 342,16 | 4 |
| Pagos Dropi (pagos@) | 0,08 | 113.615.094,00 | 110.756.669,00 | 2.858.425,08 | 13 |

0 quiebres de saldo y 0 movimientos sin concepto en las 4 wallets.

**Menpros (8.156 órdenes)** — T1: PAGADA 4.329 · PAGADA_SIN_VALIDAR 119 · PAGO_POSTERIOR_AL_REPORTE 113 · NO_APLICA 3.595.
T2: 444 COBRO_CORRECTO; reembolsos NO_APLICA 431 · REEMBOLSADO 12 · SIN_REEMBOLSO 1 (orden 88680179, 34.998).
T3: COBRADO 541 · COBRO_MAYOR_AL_FLETE 10 (Coordinadora, 10.456,26) · DIFERENCIA_TARIFA 8 (Envía, 15.804) · COBRO_ANTICIPADO 6 · COBRADO_SIN_TARIFA 4.

**Proveeduría ASIATI (8.797 órdenes)** — T1: PAGADA 5.053 · PAGADA_SIN_VALIDAR 130 · PAGO_POSTERIOR_AL_REPORTE 120 · REVERSADA 1 · NO_APLICA 3.493.
T4: COBRADO 6.633 · NO_APLICA 1.948 · COBRO_POSTERIOR_AL_REPORTE 202 · DUPLICADO 12 (30.000) · REVERSADO 2.
Órdenes de otra tienda: 13 cobros de FF (−32.500) y 10 ganancias (130.000) en órdenes de flyecommerceco@gmail.com.

**Cruce FF Proveeduría ↔ Wiilog:** 7.182 órdenes cuadran · 261 pagadas después de descargar la wallet de Wiilog ·
12 con diferencia (las mismas 12 que Wiilog tenía como "cobros de 5.000": 2.500 de flyecommerce + 2.500 de la Proveeduría).

**Intercompany:** 5 transferencias Menpros → Proveeduría (16.755.974) emparejadas; 3 RET. ADMIN Proveeduría → Wiilog (3.153.012) emparejados.

## 7. Hallazgos de septiembre

Detalle y cifras en `resultado_wallets_tiendas_pagos_septiembre.xlsx`, hoja Hallazgos.

1. CRÍTICO · Menpros: orden 88680179 sin recaudo devuelta sin reembolso del producto (34.998).
2. MEDIO · Proveeduría paga FF y recibe ganancia en órdenes de otro proveedor (flyecommerceco). Explica los 12 "cobros de 5.000" de Wiilog.
3. MEDIO · Proveeduría: 12 FF duplicados (30.000), dentro de los 98 duplicados de Wiilog.
4. MEDIO · Ajuste "BACKFILL DROP-20331": Dropi retiró ganancias ya pagadas de órdenes viejas en las tres tiendas (1.846.294,74).
5. REVISAR · Recompra Menpros (Contact Center) cubrió saldos negativos de 3 usuarios (4.489.283), uno es cliente de Wiilog.
6. REVISAR · RET. ADMIN Proveeduría → Wiilog por tiquetes y un préstamo (3.153.012).
7. REVISAR · Transferencias a cuentas destino del grupo y a personas: se categorizan a mano (46.109.579).
12. MEDIO · Coordinadora cobró la devolución por encima del flete en 10 órdenes (10.456,26); Envía cobró distinto a su fórmula en 8 (15.804).
8. INFORMATIVO · Proveeduría termina en saldo negativo.
9. INFORMATIVO · pagos@ recibe de 6 proveedores que despachan desde bodegas Wiilog: parecen pagos de servicios.
10. INFORMATIVO · El reporte de órdenes parece excluir las órdenes reemplazadas (64 reembolsos REEMPLAZADA en Menpros).
11. INFORMATIVO · Movimientos sobre órdenes de agosto: falta ese reporte.

Lo que está bien: todo lo entregado se pagó una vez, por el valor exacto, al día siguiente; todas las órdenes sin recaudo se
cobraron producto + flete exacto; el FF de la Proveeduría cuadra orden a orden con Wiilog salvo lo anterior.

## 8. Decisiones

Resueltas el 29-sep: "recompra Menpros" = Comercial Contact Center · pagos@asiati.com.co = Pagos Dropi · empresa por wallet (§1) ·
teampekop, mixmarketc y kuaimai903 son del grupo como cuentas destino · la devolución es el mismo flete (sin comisión de recaudo).

Pendientes:
1. Comisión de recaudo de Coordinadora y TCC, y por qué Coordinadora cobra más que el flete.
2. Quién paga el FF de las órdenes sin recaudo de la Proveeduría.
3. Duplicados de FF: reclamar a Dropi o ajustar entre empresas (misma decisión que Wiilog).
4. ¿Se reclama el ajuste BACKFILL DROP-20331?
5. Categoría de los RET. ADMIN de tiquetes y préstamo.
6. Correos de las demás wallets de pagos (semana del 5-oct).

## 9. Relación con PROMPT_MAESTRO V4 (lo que cambia con los datos de septiembre)

El PROMPT_MAESTRO se escribió con los archivos de julio y antes de ver las wallets de septiembre. Cuatro puntos quedan mal planteados:

| PROMPT_MAESTRO V4 | Septiembre muestra | Cambio |
|---|---|---|
| §4: la wallet ASIATI "solo recibe transferencias, sin reglas" | La Proveeduría ASIATI es **proveedor**: recibe ganancia por línea y paga FF a Wiilog (8.797 órdenes). pagos@asiati es la que solo recibe pagos. | Proveeduría = TIENDA rol PROVEEDOR; pagos@ = SOLO_PAGOS. |
| §7: `cobro_fulfillment = "SALIDA POR NUEVA ORDEN"` | "SALIDA POR NUEVA ORDEN" es el cobro de producto + flete de una orden **sin recaudo** (444 de 444 cuadran así). El FF es "SALIDA POR FULFILLMENT" y lo paga el **proveedor**, no el dropshipper (Menpros tiene 0 cobros de FF). | C2 pasa a T4 (solo rol PROVEEDOR); nueva regla T2 para sin recaudo. |
| §5.3: `ventana_gracia_dias` = 15 | 100 % de las ganancias se pagó 1 día después de la entrega, en las dos tiendas. | Ventana 2 días. Con 15, dos semanas de pagos faltantes quedarían escondidas como EN_VENTANA. |
| §4: no construir la conciliación entre wallets | El cruce FF Proveeduría ↔ Wiilog explicó los 12 "cobros de 5.000" de Wiilog y encontró FF pagado en órdenes de otro proveedor. Es barato: mismo ID de orden en las dos wallets. | Se construye ya (cruce por orden y traslados emparejados). |

Se conserva: agrupar por orden, comparar contra `GANANCIA TOTAL DE DROPSHIPPER`, sin recaudo fuera del universo de ganancia,
C0 como freno. La cascada de referencia (ID → guía → dígitos → monto) no hace falta en wallets Dropi: todo movimiento de orden
trae `ORDEN ID`; queda para bancos.

Equivalencia de reglas: C1 → T1 · C2 → T4 · C4 → T3 · C5 → catálogo con `requiere_revision` · C6 → estados DUPLICADA/DIFERENCIA dentro de
T1 y T4 · huérfanas → "fuera del reporte" con motivo · C3 (flete y comisión) no aplica a tiendas: el flete va dentro de la ganancia
(con recaudo) o del cobro de la orden (sin recaudo).

## 10. Pendiente para el núcleo

- Mover `leer_wallet` y `validar_integridad` de `wiilog/` a un módulo común (hoy `tiendas/` y `pagos/` los importan de `wiilog/`).
- Endpoint de carga por tipo de wallet y guardado de hallazgos con su gravedad.
- Pantalla de revisión: el conciliador confirma los movimientos con `requiere_revision` y escribe la observación.
