# Wallet Wiilog · reglas de conciliación

Versión 2 · reglas operativas vigentes.

Los resultados cuantitativos de cierres reales, archivos de referencia e
identificadores internos se conservan fuera de Git. El contrato para ejecutar la
regresión privada está en [BASELINE_PRIVADO.md](BASELINE_PRIVADO.md).

Parámetros versionables: `parametros_wallet_wiilog.json`.
Motor: `app/motores/conciliacion_wallets/wiilog/`.

---

## 1. Objetivo

Esta wallet es **recaudadora**: recibe lo que Wiilog cobra por su operación.

La conciliación responde:

> Todo el fulfillment y toda la comisión de flete que generamos, ¿se cobró una sola
> vez y por el valor correcto?

También clasifica las salidas para que cada movimiento tenga explicación.

El identificador de la wallet principal es configuración de entorno
(`WIILOG_WALLET_PRINCIPAL_EMAIL`) y nunca se versiona.

## 2. Fuentes

| Fuente | Patrón | Llave | Observaciones |
|---|---|---|---|
| Wallet | `historyWallet_*.xlsx` | `ORDEN ID` | Un movimiento por fila. `MONTO PREVIO` representa el saldo anterior al movimiento. |
| Órdenes | `ordenes_*.xlsx` | `ID` | Una fila por línea de producto; se agrupa por `ID` antes de cruzar. |

La columna `MARCA BLANCA` solo está disponible en el reporte que soporta la
validación de comisión de flete. Sin esa columna, ciertos casos quedan
`SIN_VERIFICAR`.

Normalización: mayúsculas, sin tildes y espacios/tabulaciones colapsados.

## 3. C0 · Integridad

| Chequeo | Regla | Si falla |
|---|---|---|
| `C0_SALDO` | Ordenado por ID del movimiento, `MONTO PREVIO(i+1) = MONTO PREVIO(i) ± MONTO(i)`; además saldo inicial + entradas − salidas = saldo final, con tolerancia de un peso. | `BLOQUEADO` |
| `C0_COBERTURA` | Hay movimientos todos los días del período hasta la fecha de corte. | `ADVERTENCIA` |
| `C0_COLUMNAS` | Existen las columnas requeridas por los parámetros. | `BLOQUEADO` |

**El saldo se ordena por ID, no por fecha.** La marca temporal puede compartir el
mismo minuto entre varios movimientos.

## 4. Conceptos de wallet

El match usa “empieza con” y, cuando corresponde, “contiene”, sobre texto
normalizado. La primera regla que empareja gana.

### Entradas

| Concepto | Patrón funcional | Categoría por defecto | Estado |
|---|---|---|---|
| `FF_GUIA_GENERADA` | Ganancia de fulfillment · `GUIA_GENERADA` | Fulfillment | Automático |
| `FF_CIERRE` | Ganancia de fulfillment · cierre entregado/devolución | Fulfillment sin recaudo | Automático |
| `FF_OTRO_USUARIO` | Pago por fulfillment de una orden | Fulfillment órdenes fuera de marca blanca | Automático |
| `FLETE_MB` | Ganancia de flete de marca blanca | Comisión flete marca blanca | Automático |
| `TRANSFERENCIA_RECIBIDA` | Retiro admin en usuario, excluyendo saldo negativo | Transferencia recibida de usuario | Revisar + observación |
| `CRUCE_RECARGA_IN` | Recarga cruzada de marca blanca | Cruce de cartera Dropi | Neto cero |
| `CRUCE_DESCUENTO_IN` | Retiro admin en usuario por saldo negativo | Cruce de cartera Dropi | Neto cero |
| `RECARGA_RECIBIDA` | Recarga de saldo en cartera | Recarga recibida | Revisar salvo emparejamiento |

### Salidas

| Concepto | Patrón funcional | Categoría por defecto | Estado |
|---|---|---|---|
| `TRASLADO_WALLET_WIILOG` | Recarga hacia la wallet principal configurada | Traslado a wallet principal Wiilog | Automático |
| `TRANSFERENCIA_ENVIADA` | Recarga hacia otro usuario por super admin | Transferencia a otro usuario por SUPER ADMIN | Revisar + observación |
| `CRUCE_RETIRO_OUT` | Retiro cruzado de marca blanca | Cruce de cartera Dropi | Neto cero |
| `FF_CORRECCION` | Corrección de entrada de fulfillment | Reverso de fulfillment | Automático |
| `RETIRO_BANCARIO` | Movimiento con `CUENTA` diligenciada | Retiro a cuenta bancaria | Automático |

### Cruces neto cero

Dropi puede usar esta wallet como puente para cubrir saldos negativos de usuarios.
Una entrada y una salida del mismo valor dentro de la ventana configurada son el
mismo hecho económico, no ingreso/egreso propio de Wiilog.

El motor empareja por:

- mismo monto;
- mismo tercero cuando la regla lo exige;
- ventana de 30 minutos.

Un cruce sin pareja queda en `REVISAR`.

### Transferencias por SUPER ADMIN

Una transferencia hacia un usuario distinto de la wallet principal, si no forma
parte de un cruce, exige observación humana antes del cierre.

El mismo criterio aplica a transferencias recibidas de usuarios.

## 5. Fulfillment

**Todo fulfillment que corresponda debe estar cobrado.**

| Elemento | Regla |
|---|---|
| Bodegas que cobran | `BODEGA` empieza por `WIILOG`, excepto Bucaramanga. |
| Con recaudo | Se cobra cuando se genera la guía. |
| Sin recaudo | Se cobra al cierre de la orden, tanto `ENTREGADO` como `DEVOLUCION`. |
| Tarifa | Depende únicamente de la bodega. |
| Bogotá | 2.500. |
| Bogotá 3.0 | 3.250. |
| Bogotá 2.0 | Pendiente de confirmar. |
| Medellín 2.0 | Pendiente de confirmar. |
| Ventana de gracia | Un día. |
| Rechazadas | El cobro y reverso es correcto; queda `REVERSADO` informativo. |
| Bucaramanga | No cobra fulfillment; un cobro allí es `COBRADO_NO_CORRESPONDE`. |

Estados:

- `COBRADO`
- `NO_COBRADO`
- `DUPLICADO`
- `DIFERENCIA_TARIFA`
- `COBRADO_NO_CORRESPONDE`
- `EN_VENTANA`
- `PENDIENTE_CIERRE`
- `REVERSADO`
- `NO_APLICA`

Del lado de la wallet también existen `FUERA_DEL_REPORTE` y
`FUERA_MARCA_BLANCA`.

## 6. Comisión de flete de marca blanca

| Elemento | Regla |
|---|---|
| Valor | 1.000 pesos por guía. |
| Momento | Cuando la guía cierra como `ENTREGADO` o `DEVOLUCION`. |
| Universo | Guías creadas nativamente desde marca blanca. |
| Excepción | No se cobra cuando la transportadora es `WIILOG`. |
| Evidencia requerida | Columna `MARCA BLANCA` para afirmar `NO_COBRADO`. |

Estados:

- `COBRADO`
- `NO_COBRADO`
- `DUPLICADO`
- `DIFERENCIA_VALOR`
- `COBRADO_NO_CORRESPONDE`
- `SIN_VERIFICAR`
- `PENDIENTE_CIERRE`
- `NO_APLICA`

## 7. Regresión con datos reales

El motor fue validado contra un cierre real. Los Excel, identificadores y cifras
esperadas pertenecen al paquete privado de regresión y no se almacenan en Git.

`tests/wallet_wiilog/test_regresion_septiembre.py`:

1. busca una exportación de órdenes y una exportación de wallet en
   `fixtures/wallet_wiilog/2026-09/`;
2. carga `expected_baseline.json` desde la misma carpeta;
3. ejecuta el motor con las reglas versionadas;
4. compara C0, conteos, montos en juego, estados y cruces contra ese baseline.

Si cambia una regla de negocio de forma aprobada, se actualizan juntos el motor,
la explicación de la decisión y el baseline privado.

## 8. Decisiones operativas

### Cerradas

- Bucaramanga no cobra fulfillment.
- La tarifa de fulfillment depende solo de la bodega.
- La devolución sin recaudo genera cobro; si no llega, se reclama.
- En órdenes rechazadas, el reverso de fulfillment es correcto e informativo.

### Abiertas

- Tratamiento operativo de fulfillment cobrado dos veces.
- Tratamiento de diferencias de tarifa.
- Confirmar tarifas de Bogotá 2.0 y Medellín 2.0.
- Confirmar el soporte de órdenes fuera del reporte disponible.
- Incluir suficiente margen temporal de órdenes para explicar cobros de períodos
  anteriores.
- Obtener el reporte con `MARCA BLANCA` cuando se requiera verificar flete.
- Exigir soporte para transferencias manuales que queden en revisión.

## 9. Regla de seguridad de datos

En Git se conservan reglas, contratos, estados y tests sintéticos.

No se versionan:

- archivos operativos;
- saldos o montos de cierres reales;
- conteos de hallazgos reales;
- correos/identificadores internos de wallets;
- IDs concretos de órdenes o guías usados como evidencia.

La evidencia cuantitativa queda en almacenamiento privado y en los snapshots
auditables de la plataforma.
