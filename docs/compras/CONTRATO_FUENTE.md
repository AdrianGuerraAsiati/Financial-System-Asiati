# Contrato técnico de fuente — Compras / Supply Chain

**Fuente:** Google Sheets `INFORME COMPRAS 2024-2026`  
**Modo:** solo lectura  
**Decisión:** `docs/decisiones/0005-compras-google-sheets-solo-lectura.md`

## 1. Objetivo

Evitar que un cambio manual en encabezados, hojas o estructura produzca resultados silenciosamente incorrectos en la plataforma.

La plataforma consume tres hojas:

- `INFORME CLIENTES (CO)`
- `INFORME CLIENTES (EC)`
- `INFORME CLIENTES (CL)`

El país se deriva de la hoja.

## 2. Campos críticos

Si desaparece cualquiera de estos campos, la lectura operativa de Compras se bloquea:

- `NUMERO OC`
- `CLIENTE`
- `PROVEEDOR`
- `ESTADO`
- `MODO TRANSPORTE`

El endpoint de diagnóstico sigue disponible para explicar el problema.

Los campos consumidos no críticos incluyen, entre otros:

- `SKU`
- `DESCRIPCION`
- documento de transporte;
- ETD;
- ETA;
- fecha de entrega a bodega destino;
- `VALOR TOTAL COMPRA USD`;
- `VALOR OCI (DDP)`.

La ausencia de un campo no crítico aparece como advertencia de contrato, pero no bloquea por sí sola la lectura.

## 3. Encabezados duplicados

Dos encabezados que normalicen al mismo valor se consideran un cambio crítico.

Ejemplo:

```
ESTADO
ESTADO 
```

Si ambos existen simultáneamente, la plataforma bloquea la lectura operativa para evitar decidir arbitrariamente cuál columna manda.

## 4. Campos no consumidos

La fuente contiene más columnas de las que usa el primer vertical técnico.

Los encabezados no consumidos:

- se reportan en diagnóstico;
- no se eliminan de la fuente;
- no se consideran automáticamente errores;
- pueden incorporarse al contrato cuando exista una necesidad funcional.

## 5. Snapshot y cache

Cada lectura completa consulta CO, EC y CL y produce un snapshot en memoria.

Configuración:

```
COMPRAS_SHEETS_CACHE_SECONDS=60
```

Durante el TTL, los endpoints reutilizan el mismo snapshot para evitar lecturas repetitivas contra Google Sheets.

El cache:

- no escribe al Sheet;
- no es una base de datos;
- no es fuente de verdad;
- se pierde al reiniciar el proceso;
- puede forzarse a releer desde el diagnóstico.

## 6. Trazabilidad por línea

Cada línea normalizada conserva:

- `pais`;
- `hoja_fuente`;
- `fila_fuente`;
- `estado_origen`;
- `modo_transporte_origen`;
- valores monetarios originales como texto.

Las normalizaciones viven en campos separados.

## 7. Calidad de datos

Las reglas técnicas actuales son observacionales. No corrigen la fuente ni afirman por sí solas que exista un error de negocio.

Códigos iniciales:

- `OC_NO_IDENTIFICADA`
- `CLIENTE_VACIO`
- `PROVEEDOR_VACIO`
- `ESTADO_VACIO`
- `ESTADO_POR_DEFINIR`
- `TRANSPORTE_VACIO`
- `TRANSPORTE_NO_CATALOGADO`
- `ENTREGA_CON_ESTADO_NO_RECIBIDO`

Cada resultado incluye muestras con país, hoja, fila y OC para facilitar revisión manual.

## 8. Agrupación por OC

La plataforma puede agrupar líneas para exploración, pero no asigna todavía un único estado financiero/logístico a una OC.

La respuesta por OC expone:

- proveedores observados;
- estados observados;
- etapas observadas;
- modos de transporte;
- banderas `estado_mixto`, `proveedor_mixto`, `transporte_mixto`.

Las líneas `N/A` o sin número de OC **no se agrupan entre sí**; cada fila conserva identidad propia.

## 9. Endpoints

Todos requieren `compras.ver`.

```
GET /api/v1/compras/fuente/estado
GET /api/v1/compras/catalogos
GET /api/v1/compras/calidad
GET /api/v1/compras/resumen
GET /api/v1/compras/kpis
GET /api/v1/compras/dashboard
GET /api/v1/compras/atencion
GET /api/v1/compras/validacion/tablero
GET /api/v1/compras/export.zip
GET /api/v1/compras/ocs
GET /api/v1/compras/lineas
```

`/fuente/estado?forzar_lectura=true` relee Google Sheets ignorando el snapshot vigente. Sigue siendo una operación de lectura.

`/resumen` expone únicamente conteos estructurales (líneas, OCs identificadas, OCs mixtas, líneas sin OC y líneas con etapa por definir).

`/kpis` expone las dos familias monetarias descriptivas. Cada familia se marca como no disponible si su columna fuente falta en alguna hoja del alcance solicitado; no se suman países parcialmente sin advertencia.

## 10. Fuera de este contrato

Este bloque no decide:

- valor en tránsito;
- valor en el mar;
- valor pagado;
- saldo proveedor;
- definición de OC cerrada;
- tratamiento financiero de OC parcial;
- significado definitivo de `EN OTM`;
- significado definitivo de `PENDIENTE DEPÓSITO`;
- significado definitivo de `PENDIENTE INVIMA`.

Esas decisiones siguen en `docs/compras/PREGUNTAS_NEGOCIO.md`.


## 11. Vista derivada Supply Chain como referencia de regresión

La configuración puede incluir:

```dotenv
COMPRAS_SHEETS_SUPPLY_CHAIN_RANGE='Supply Chain'!A:Z
```

Esa hoja se lee con el mismo scope `spreadsheets.readonly`.

No forma parte del snapshot primario de líneas y no reemplaza CO/EC/CL. Se utiliza únicamente para comparar DDP por estado cuando el pivote contiene suficiente contexto para identificar país, estado y valor sin asumir coordenadas fijas.
