# Dashboard ejecutivo y validación — Compras / Supply Chain

**Estado:** implementado como vista descriptiva read-only  
**Fuente primaria:** hojas de detalle CO / EC / CL  
**Referencia de validación:** hoja derivada `Supply Chain`

## 1. Propósito

Convertir el explorador técnico de Compras en una vista que pueda revisarse como producto sin cerrar por código decisiones que siguen perteneciendo a negocio.

La vista ejecutiva muestra únicamente conceptos que pueden sostenerse con la fuente actual:

- costo de compra de la población actual;
- valor comercial DDP de la población actual;
- OCs con al menos una línea dentro de esa población;
- observaciones objetivas que requieren revisión;
- distribución por estado y transporte;
- detalle de OCs y líneas;
- comparación read-only contra el tablero derivado actual.

No se muestra todavía una tarjeta llamada `valor en tránsito` o `valor en el mar`.

## 2. Población actual

Se conserva la población ya documentada desde el pivote `Supply Chain`:

- `EN BODEGA ASIATI SHENZHEN`
- `EN BODEGA ASIATI YIWU`
- `EN NACIONALIZACION`
- `EN OTM`
- `EN PRODUCCION`
- `ENVIADO A DESTINO`
- `PENDIENTE DEPOSITO`

La interfaz usa el texto **población actual** precisamente para evitar afirmar que esta sea la definición corporativa definitiva de “activo”.

Asimismo, “OCs con líneas en población actual” significa:

> cantidad de llaves `(pais, numero_oc)` identificadas con por lo menos una línea dentro de los estados anteriores.

No equivale todavía a una regla corporativa de “OC activa”.

## 3. Puntos de atención implementados

Los puntos de atención son observaciones objetivas. No tienen severidad y no corrigen Google Sheets.

Reglas:

### Documentación / fechas

- `ENVIADA_SIN_DOCUMENTO`: `ENVIADO A DESTINO` sin documento de transporte.
- `ENVIADA_SIN_ETD`: `ENVIADO A DESTINO` sin ETD.
- `ENVIADA_SIN_ETA`: `ENVIADO A DESTINO` sin ETA.
- `ETA_VENCIDA_SIN_ENTREGA`: ETA anterior a hoy, sin fecha de entrega, no recibida y no anulada.
- `ETA_NO_INTERPRETABLE`: existe ETA, pero no coincide con un formato soportado; no se usa para decidir vencimiento.
- `ENTREGA_CON_ESTADO_ABIERTO`: existe fecha de entrega a bodega, pero la etapa aún no es `RECIBIDO`.

Formatos de fecha reconocidos:

- `YYYY-MM-DD`
- `YYYY/MM/DD`
- `DD/MM/YYYY`
- `DD-MM-YYYY`
- variantes anteriores con hora `HH:MM:SS` donde aplica.

No se adivina una fecha si el valor no puede interpretarse.

### Composición de OC

- `OC_ESTADOS_MIXTOS`
- `OC_PROVEEDORES_MULTIPLES`
- `OC_TRANSPORTES_MULTIPLES`

Estas reglas describen la composición real de la OC. No calculan un estado agregado.

## 4. Validación contra la hoja `Supply Chain`

Variable de entorno:

```dotenv
COMPRAS_SHEETS_SUPPLY_CHAIN_RANGE='Supply Chain'!A:Z
```

La plataforma lee esa vista con el mismo cliente read-only.

El parser busca un pivote que pueda identificar sin asumir posiciones fijas:

1. encabezado `ESTADO`;
2. una columna cuyo encabezado contenga `VALOR OCI` y `DDP`;
3. un país identificable cerca del pivote: CO/Colombia, EC/Ecuador o CL/Chile.

Si no puede identificar esas tres cosas, la comparación queda `no disponible`; no se compara contra un pivote ambiguo.

Cuando sí puede:

```
detalle CO/EC/CL
 -> suma exacta DDP por estado de la población actual
 -> compara con SUM de VALOR OCI (DDP) del pivote
```

Resultados por estado:

- `COINCIDE`
- `DIFERENCIA`
- `SOLO_DETALLE`
- `SOLO_TABLERO`

La igualdad se evalúa al centavo con `Decimal`.

La hoja derivada sirve como **referencia de regresión**, no como nueva fuente primaria.

## 5. Exportación

Endpoint:

```
GET /api/v1/compras/export.zip?empresa_id=<id>
```

El ZIP contiene:

- `compras_lineas.csv`
- `compras_ocs.csv`
- `compras_puntos_atencion.csv`
- `compras_kpis.csv`

Los archivos usan UTF-8 con BOM para facilitar apertura en herramientas de escritorio.

El export no escribe a Google Sheets ni altera la fuente.

## 6. Endpoints nuevos

Todos requieren `compras.ver`.

```
GET /api/v1/compras/dashboard
GET /api/v1/compras/atencion
GET /api/v1/compras/validacion/tablero
GET /api/v1/compras/export.zip
```

`dashboard` y `atencion` aceptan `pais=CO|EC|CL`.

`validacion/tablero?forzar_lectura=true` fuerza una nueva lectura de la hoja derivada, manteniendo el modo read-only.

## 7. Límites deliberados

Este bloque no resuelve:

- definición corporativa de OC activa;
- valor en tránsito / valor en el mar;
- jerarquía ejecutiva DDP vs costo;
- severidad de alertas;
- significado final de EN OTM;
- significado final de PENDIENTE DEPÓSITO;
- tratamiento de PENDIENTE INVIMA;
- pagado o saldo a proveedor;
- escritura a Google Sheets.

Las dudas correspondientes siguen en `REPORTE_DUDAS_JUANFE_KPIS.md`.
