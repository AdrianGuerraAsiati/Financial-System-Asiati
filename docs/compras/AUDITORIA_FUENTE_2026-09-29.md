# Auditoría de fuente y huecos de desarrollo — Compras / Supply Chain

**Fecha de revisión:** 29 de septiembre de 2026  
**Fuente revisada:** Google Sheets `INFORME COMPRAS 2024-2026`  
**Alcance:** lectura y análisis solamente; no se modificó la fuente.

## 1. Objetivo

Separar tres cosas que no deben confundirse:

1. calidad y cobertura de los datos operativos;
2. confiabilidad de las vistas derivadas actuales del Google Sheet;
3. huecos técnicos que debe cubrir la plataforma antes de tratar Compras como un módulo financiero trazable.

Los vacíos reportados aquí son observaciones de fuente. Un campo vacío no se clasifica automáticamente como error contable.

## 2. Población operativa confirmada

Las hojas de detalle siguen siendo la base más confiable para la plataforma:

| País | Líneas sustantivas |
|---|---:|
| CO | 2.084 |
| EC | 76 |
| CL | 99 |
| **Total** | **2.259** |

Se mantienen 705 agrupaciones de OC identificadas por país en el baseline técnico.

La granularidad correcta continúa siendo línea/producto. En el mismo conjunto existen:

- 214 OCs con más de un proveedor;
- 32 OCs con más de un estado;
- 46 OCs con más de un modo de transporte.

Por lo tanto, la plataforma no debe reducir una OC a una sola fila ni asumir un único proveedor, estado o embarque.

## 3. Cobertura de campos observada

Sobre las 2.259 líneas sustantivas:

| Campo | Vacíos observados | % aprox. |
|---|---:|---:|
| SKU | 174 | 7,7% |
| Proveedor | 19 | 0,8% |
| Valor total compra USD | 82 | 3,6% |
| Valor OCI/DDP | 59 | 2,6% |
| Fecha pago total en China | 1.570 | 69,5% |
| Fecha solicitud pago (abono) | 2.259 | 100,0% |

En líneas con estado `ENTREGADO`:

- 1.368 líneas no tienen fecha de pago total en China;
- 298 líneas no tienen `FACTURA` de destino.

Estas cifras no prueban por sí mismas una omisión contable. Sí impiden inferir, sin otra fuente, conceptos como saldo a proveedor, pagado a proveedor o completitud documental definitiva.

## 4. Vistas derivadas: controles detectados

Las vistas derivadas no deben convertirse en source of truth automático.

### `Supply Chain `

La validación por metadata de pivote ya identifica correctamente los bloques CO / CL / EC.

Resultado de regresión observado:

- 10 comparaciones de DDP por país/estado coinciden al centavo;
- existe una diferencia descriptiva en CL: `PENDIENTE DEPOSITO` por USD 3.450 aparece en detalle y no en el pivote actual.

La plataforma debe exponer esa diferencia; no corregirla silenciosamente.

### `RESUMEN`

En el rango completo visible A:AB se observaron:

- **2.064 celdas `#REF!`**;
- distribuidas en **172 filas**;
- el bloque afectado corresponde a una sección derivada de proveedores/valor.

No portar esas fórmulas rotas a la plataforma.

### `Calc_Data`

Se observaron:

- **5 celdas `#REF!`**;
- distribuidas en 4 filas;
- afectan celdas de métricas/resúmenes derivados.

### `KPIs`

Se observó al menos:

- **1 `#DIV/0!`**.

### `Dashboard_Final`

En el rango disponible solo se observa el encabezado/título del dashboard; no constituye una referencia funcional completa para reconstruir la plataforma.

## 5. `REPORTE OC`

Se observaron 216 filas de OC:

- 183 Colombia;
- 17 Chile;
- 9 Ecuador;
- 7 Brasil.

No cubre todo el universo de 705 OCs del detalle CO/EC/CL, por lo que se considera fuente auxiliar hasta definir formalmente su alcance.

La hoja sí contiene información potencialmente útil para una fase posterior:

- moneda;
- valor total de OC;
- modalidad;
- condiciones de pago;
- términos de pago estandarizados;
- comercial;
- estado de embarque.

También contiene OCs en COP y USD. No comparar sus montos directamente contra campos USD del detalle sin una regla explícita de moneda/conversión.

## 6. Huecos de desarrollo cerrados

### PR #66 — snapshots auditables

Implementado:

- captura fresca y persistente del Google Sheet;
- hash SHA-256 del contenido para idempotencia;
- snapshot de diagnóstico/rangos;
- persistencia de filas crudas sustantivas y normalizadas;
- histórico por empresa;
- auditoría del guardado;
- Google Sheets continúa estrictamente read-only.

Esto permite responder qué datos sustentaban una lectura en un momento determinado sin convertir la base de datos en la fuente operativa primaria.

### PR #67 — trazabilidad y cobertura

Implementado:

- ampliación del contrato de línea con datos de producto, compra, producción, logística y responsables;
- separación entre encabezado consumido y encabezado que define una fila sustantiva;
- cobertura descriptiva de campos para:
  - total;
  - población actual;
  - entregados;
- timeline por línea de una OC;
- próximas llegadas por ETA interpretable;
- parser común de fechas.

El `CBM` duplicado de EC/CL permanece deliberadamente sin normalización canónica hasta definir cuál columna manda. El crudo queda preservado en snapshots.

### PR #68 — controles en UI

Implementado:

- cobertura de datos visible;
- próximas llegadas;
- timeline al abrir una OC;
- listado de capturas auditables;
- guardado manual de una captura desde Compras.

## 7. Huecos que siguen abiertos por definición de negocio

No cerrar por código:

1. significado logístico definitivo de `EN OTM`;
2. significado de `PENDIENTE DEPOSITO`;
3. tratamiento de `PENDIENTE INVIMA`;
4. definición de “valor en tránsito / valor en el mar”;
5. familia monetaria oficial de ese KPI;
6. criterio de OC parcial/cerrada;
7. tolerancias para atraso de producción y ETA;
8. significado contable definitivo de `FACTURA` de destino;
9. fuente de montos reales de abonos/pagos a proveedor;
10. tratamiento de moneda de `REPORTE OC`;
11. columna canónica de CBM en EC/CL.

## 8. Límite contable actual

Con la fuente actual la plataforma puede sostener:

- costo de compra;
- DDP;
- distribución por estado;
- trazabilidad logística;
- próximas ETA;
- controles de cobertura y documentación;
- comparación contra vistas derivadas;
- evidencia histórica de lo leído.

Todavía **no** puede sostener con integridad:

- pagado a proveedor en dinero;
- saldo pendiente a proveedor;
- cuentas por pagar;
- cash-flow de compras;
- conciliación pago-proveedor.

Una fecha de pago o abono no demuestra por sí sola el monto pagado.

## 9. Próximo paso recomendado

Antes de ampliar KPIs financieros, definir con negocio:

1. estados corporativos y OC parcial;
2. fuente de pagos/abonos a proveedor;
3. moneda y alcance de `REPORTE OC`;
4. CBM canónico de EC/CL.

Mientras esas definiciones se cierran, el desarrollo seguro puede continuar en controles documentales, UX de trazabilidad y comparación histórica entre snapshots.
