# Wallet Wiilog · reglas de conciliación

Versión 2 · 28 de septiembre de 2026 · Reglas: Juan Felipe Parra · Mapeo y validación: corrida sobre septiembre 2026

**Cambios de la versión 2:** Bucaramanga no cobra fulfillment; la tarifa depende solo de la bodega (Bogotá 2.500, Bogotá 3.0 3.250, Bogotá 2.0 y Medellín 2.0 por confirmar); la devolución sin recaudo sin cobro se reclama; el reverso en rechazadas es correcto.

Parámetros: `parametros_wallet_wiilog.json` (mismo directorio).
Motor de referencia: `app/motores/conciliacion_wallets/wiilog/` — Python puro, probado con septiembre.

---

## 1. Qué es esta wallet

La wallet del usuario `marcablanca@wiilog.com.co` en Dropi. Es **recaudadora**: recibe lo que Wiilog cobra por su operación. La conciliación responde una pregunta:

> **Todo el fulfillment y toda la comisión de flete que generamos, ¿se cobró? ¿Una sola vez y por el valor correcto?**

Y ordena las salidas para que cada peso que sale tenga categoría y explicación.

## 2. Las dos fuentes

| Fuente | Archivo de Dropi | Llave | Observaciones |
|---|---|---|---|
| Wallet | Historial de la wallet (`historyWallet_*.xlsx`) | `ORDEN ID` | Un movimiento por fila. `MONTO PREVIO` es el saldo antes del movimiento. Sin `ORDEN ID` en movimientos no operativos: se toma de la descripción cuando aparece. |
| Órdenes | Reporte de órdenes (`ordenes_*.xlsx`) | `ID` | **Una fila por línea de producto:** se agrupa por `ID` antes de cruzar (septiembre: 26.331 filas → 23.093 órdenes). La columna `MARCA BLANCA` solo viene en el reporte que comparte el KAM de Dropi. |

Normalización obligatoria: mayúsculas, sin tildes, espacios y tabulaciones colapsados. La bodega llega como `WIILOG MEDELLÍN\t 2.0`.

## 3. C0 · Integridad (freno)

| Chequeo | Regla | Si falla |
|---|---|---|
| `C0_SALDO` | Ordenado por **ID del movimiento**, `MONTO PREVIO(i+1) = MONTO PREVIO(i) ± MONTO(i)` en todas las filas, y saldo inicial + entradas − salidas = saldo final (tolerancia 1 peso). | BLOQUEADO |
| `C0_COBERTURA` | Hay movimientos todos los días del período hasta la fecha de corte. | ADVERTENCIA |
| `C0_COLUMNAS` | Están las columnas del parámetro. | BLOQUEADO |

**Ordenar por ID, no por fecha.** La fecha viene al minuto y varios movimientos comparten minuto: ordenado por fecha, septiembre muestra 288 quiebres falsos; por ID, cero.

## 4. Mapeo de la wallet (septiembre, 33.846 movimientos)

Match por "empieza con" y "contiene" sobre el texto normalizado. El primero que empareja gana.

### Entradas

| Concepto | Texto de Dropi (empieza con) | Mov. | Monto | Categoría por defecto | Estado |
|---|---|---|---|---|---|
| `FF_GUIA_GENERADA` | PAGO POR GANANCIA COMISION FULFILLMENT DE MARCA BLANCA … CONCEPTO: GUIA_GENERADA | 18.563 | $46.439.998 | Fulfillment | Automático |
| `FF_CIERRE` | … COMISION FULFILLMENT … CONCEPTO: ENTREGADO | 694 | $1.756.750 | Fulfillment sin recaudo | Automático |
| `FF_OTRO_USUARIO` | PAGO POR FULFILLMENT, ORDEN ID | 1.461 | $3.652.500 | Fulfillment órdenes fuera de marca blanca | Automático |
| `FLETE_MB` | PAGO POR GANANCIA FLETE DE MARCA BLANCA (ENTREGADO o DEVOLUCION) | 13.040 | $13.040.000 | Comisión flete marca blanca | Automático |
| `TRANSFERENCIA_RECIBIDA` | ENTRADA POR RETIRO ADMIN EN USER … (sin "saldo negativo") | 5 | $10.165.060 | Transferencia recibida de usuario | **Revisar + observación** |
| `CRUCE_RECARGA_IN` | ENTRADA POR RECARGA CRUZADA DE MARCA BLANCA | 9 | $6.432.411 | Cruce de cartera Dropi | Neto cero |
| `CRUCE_DESCUENTO_IN` | ENTRADA POR RETIRO ADMIN EN USER … SALDO NEGATIVO | 8 | $5.066.580 | Cruce de cartera Dropi | Neto cero |
| `RECARGA_RECIBIDA` | RECARGA DE SALDO EN CARTERA | 1 | $300.000 | Recarga recibida | Revisar, salvo que se empareje |

### Salidas

| Concepto | Texto de Dropi (empieza con) | Mov. | Monto | Categoría por defecto | Estado |
|---|---|---|---|---|---|
| `TRASLADO_WALLET_WIILOG` | SALIDA POR RECARGA DE SALDO EN CARTERA AL USUARIO wiilogwallet@wiilog.com.co | 10 | $34.032.439 | Traslado a wallet principal Wiilog | Automático |
| `TRANSFERENCIA_ENVIADA` | SALIDA POR RECARGA DE SALDO EN CARTERA AL USUARIO {otro}, POR SUPER ADMIN | 15 | $11.926.426 | **Transferencia a otro usuario por SUPER ADMIN** | **Revisar + observación** (10 se emparejan como cruce) |
| `CRUCE_RETIRO_OUT` | SALIDA POR RETIRO CRUZADO DE MARCA BLANCA | 8 | $5.066.580 | Cruce de cartera Dropi | Neto cero |
| `FF_CORRECCION` | CORRECCIÓN DE ENTRADA DE FULFILLMENT | 32 | $82.500 | Reverso de fulfillment | Automático |
| `RETIRO_BANCARIO` | Movimiento con `CUENTA` diligenciada | 0 | — | Retiro a cuenta bancaria | Automático |

**No hubo retiros directos a cuenta bancaria en septiembre** (`CUENTA` y `CONCEPTO DE RETIRO` vacíos). La salida de plata hacia Wiilog se hizo trasladando saldo a `wiilogwallet@wiilog.com.co`.

### Cruces neto cero

Dropi usa esta wallet como puente para cubrir saldos negativos de usuarios: entra un valor y sale el mismo valor en minutos, hecho por "Recuperación de cartera" de Dropi. No es ingreso ni egreso de Wiilog. El motor empareja entrada y salida por **mismo monto, mismo tercero cuando aplica, ventana de 30 minutos**. En septiembre: 18 parejas por $11.798.991 de cada lado, entre recargas cruzadas (9), descuentos por saldo negativo (8) y una recarga de $300.000 reenviada a otro usuario 2 minutos después (1). Un cruce sin pareja queda en Revisar.

### Transferencias por SUPER ADMIN (categoría diferencial)

Toda salida "POR SUPER ADMIN" a un usuario distinto de la wallet principal de Wiilog, y que no sea parte de un cruce, queda:
- categoría **Transferencia a otro usuario por SUPER ADMIN**,
- estado **Revisar**,
- **Observación obligatoria**: el conciliador escribe para qué fue (préstamo, pago, reembolso…) antes de poder cerrar el período.
- El tercero (correo) se extrae de la descripción.

Lo mismo para las **transferencias recibidas** de usuarios. Septiembre trae: 5 enviadas ($5.194.015) y 5 recibidas ($10.165.060), varias con motivo en el texto ("Tiquete…", "Préstamo…", "A solicitud de…").

## 5. Regla FF · Fulfillment

**Todo lo que generemos de fulfillment debe estar cobrado.**

| Elemento | Regla |
|---|---|
| Quién cobra | Órdenes despachadas desde bodegas Wiilog: `BODEGA` empieza con `WIILOG`, **excepto Bucaramanga**, que no cobra fulfillment. Las bodegas externas no generan FF. Un cobro en Bucaramanga es `COBRADO_NO_CORRESPONDE`. |
| Cuándo, con recaudo | Al generarse la guía (`FECHA GENERACION DE GUIA`). Concepto `…CONCEPTO: GUIA_GENERADA`. |
| Cuándo, sin recaudo | Al cerrar la orden: `ENTREGADO` o `DEVOLUCION` (`FECHA ENTREGADO` / `FECHA DEVOLUCION`). Concepto `…CONCEPTO: ENTREGADO`. Dropi solo paga al entregar: **la devolución sin cobro se reclama** (`NO_COBRADO`). |
| Cuánto | **Solo depende de la bodega**, no del tipo de envío ni del cliente: Bogotá 2.500 · Bogotá 3.0 3.250 · Bogotá 2.0 y Medellín 2.0 por confirmar (se acepta el cobro que llegue y se marca la tarifa como pendiente). Cualquier otro valor es `DIFERENCIA_TARIFA`. |
| Ventana | 1 día: en septiembre el 100 % de los cobros entró el mismo día de la guía. |
| Rechazadas | Dropi cobra y reversa (`CORRECCIÓN DE ENTRADA DE FULFILLMENT`). **Es correcto**: `REVERSADO`, informativo. |

Estados: `COBRADO` · `NO_COBRADO` (crítico) · `DUPLICADO` (medio) · `DIFERENCIA_TARIFA` (medio) · `COBRADO_NO_CORRESPONDE` (medio) · `EN_VENTANA` · `PENDIENTE_CIERRE` · `REVERSADO` · `NO_APLICA`.
Del lado de la wallet: `FUERA_DEL_REPORTE` (orden no está en el reporte de órdenes) y `FUERA_MARCA_BLANCA` (pago "PAGO POR FULFILLMENT").

## 6. Regla FLETE · Comisión de flete marca blanca

| Elemento | Regla |
|---|---|
| Cuánto | 1.000 pesos por guía. |
| Cuándo | Cuando la guía cierra: `ENTREGADO` o `DEVOLUCION`. |
| Qué guías | Solo las creadas nativamente desde la marca blanca: columna `MARCA BLANCA` del reporte del KAM de Dropi. |
| Excepción | No se cobra en transportadora `WIILOG`. |

Estados: `COBRADO` · `NO_COBRADO` (crítico, solo con la columna MARCA BLANCA) · `DUPLICADO` · `DIFERENCIA_VALOR` · `COBRADO_NO_CORRESPONDE` (transportadora WIILOG o guía no nativa) · `SIN_VERIFICAR` (cerrada sin cobro y sin columna MARCA BLANCA) · `PENDIENTE_CIERRE` · `NO_APLICA`.

## 7. Línea base · septiembre 2026 (test de regresión)

Archivos: `ordenes_sept_20260928_144134.xlsx` y `historyWallet_20260928_142641.xlsx`. Corte 28-sep-2026 14:12. **Viven en `fixtures/`, fuera de git.** El motor tiene que reproducir exactamente:

```
C0_SALDO            EN_ORDEN · saldo inicial 3.000,72 · entradas 86.853.298,80 · salidas 51.107.944,97 · final 35.748.354,55
Órdenes agrupadas   23.093 (26.331 filas)

FF · órdenes de bodegas Wiilog (parámetros v2)   22.884
  COBRADO                                 17.634
  NO_COBRADO                                   8      $20.750   (devoluciones sin recaudo: Bogotá 7 · Bogotá 3.0 1)
  DUPLICADO                                   98     $245.000
  DIFERENCIA_TARIFA                           12      $30.000   (Bogotá cobradas a 5.000)
  EN_VENTANA                                  20
  PENDIENTE_CIERRE                            71
  REVERSADO                                   25
  NO_APLICA                                5.016   (incluye las 870 de Bucaramanga)
FF cobrado sin orden en el reporte
  FUERA_DEL_REPORTE                        1.333   $3.461.249,87
  FUERA_MARCA_BLANCA                       1.461   $3.652.499,94

FLETE · órdenes del reporte
  COBRADO 8.991 · SIN_VERIFICAR 4.268 · PENDIENTE_CIERRE 3.234 · NO_APLICA 6.600
  cobrado sin orden en el reporte          4.049   $4.049.000

Movimientos por revisar (observación obligatoria)   10
Cruces neto cero emparejados                         18 parejas
```

Si el motor no da estas cifras con estos archivos, el motor está mal, no los datos. Si una regla cambia a propósito, la línea base se actualiza en el mismo PR con la explicación.

## 8. Decisiones

### Cerradas el 28 de septiembre de 2026 (Juan Felipe)

| # | Tema | Decisión | Efecto en septiembre |
|---|---|---|---|
| 1 | Bucaramanga | No cobra fulfillment. | Sus 870 órdenes pasan a `NO_APLICA`; ya no hay 677 no cobradas. |
| 2 | Tarifas | Solo dependen de la bodega. Bogotá 2.500, Bogotá 3.0 3.250, Bogotá 2.0 y Medellín 2.0 por confirmar. | Los 24 cobros de 3.250 en Bogotá 3.0 son correctos. Los 12 cobros de 5.000 en Bogotá son `DIFERENCIA_TARIFA` ($30.000 de más). |
| 3 | Devolución sin recaudo | Se cobra y, si no llega, se reclama. | 8 órdenes `NO_COBRADO`, $20.750. |
| 4 | Rechazadas | El reverso de Dropi es correcto. | 25 órdenes `REVERSADO`, informativo. |

### Abiertas

| # | Hallazgo | Cifra | Pregunta | Decide |
|---|---|---|---|---|
| 5 | **FF cobrado dos veces** en la misma orden, misma guía, mismo minuto. | 98 órdenes · $245.000 (más 63 fuera del reporte) | Se le cobró de más al cliente: ¿se devuelve o se reporta a Dropi? | Juan Felipe |
| 6 | **Cobros de 5.000 en Bogotá.** | 12 órdenes · $30.000 | ¿Se reclama la diferencia a Dropi o se devuelve al cliente? | Juan Felipe |
| 7 | **Tarifas de Bogotá 2.0 y Medellín 2.0.** | Sin cobros en septiembre | Confirmar el valor. | Juan Felipe |
| 8 | **"PAGO POR FULFILLMENT"** de órdenes que no están en el reporte de marca blanca. | 1.461 · $3.652.500 | ¿Son órdenes de usuarios Dropi despachadas desde bodegas Wiilog? Hace falta su reporte. | Juan Felipe |
| 9 | **Órdenes de agosto cobradas en septiembre.** | 1.333 · $3.461.250 | Descargar órdenes con un mes de margen hacia atrás. | Operación |
| 10 | **Flete sin verificar.** | 4.268 guías cerradas sin comisión | Pedir a Jorge (KAM Dropi) el reporte con la columna MARCA BLANCA. | Operación |
| 11 | **Transferencias por SUPER ADMIN.** | 5 enviadas $5.194.015 · 5 recibidas $10.165.060 | Soporte de cada una. | Conciliador |
