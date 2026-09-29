# SPEC funcional — Compras / Supply Chain

**Estado:** borrador funcional  
**Fecha:** 28 de septiembre de 2026  
**Fuente operativa oficial temporal:** Google Sheets — `INFORME COMPRAS 2024-2026`

---

## 1. Objetivo

Definir la lógica de negocio del módulo de Compras / Supply Chain antes de construir UI, persistencia propia o automatizaciones de escritura.

El módulo debe permitir responder, como mínimo:

- qué órdenes de compra existen;
- qué productos/SKU contiene cada OC;
- qué proveedor corresponde a cada línea;
- en qué etapa logística está cada línea;
- qué valor económico está en producción, tránsito, destino, nacionalización o recibido;
- qué operaciones requieren atención;
- qué mercancía se espera recibir y cuándo.

Por decisión corporativa vigente, **no se reemplaza ni rediseña la fuente actual**. La plataforma lee el Google Sheet tal como existe y aplica una capa de normalización y lógica encima. Además, la fuente es **estrictamente de solo lectura** para la plataforma; ver `docs/decisiones/0005-compras-google-sheets-solo-lectura.md`.

---

## 2. Fuente y granularidad

### 2.1 Hojas de detalle

Las hojas principales son:

- `INFORME CLIENTES (CO)`
- `INFORME CLIENTES (EC)`
- `INFORME CLIENTES (CL)`

El país se deriva de la hoja de origen.

### 2.2 Granularidad real

La unidad mínima de análisis es una **línea de compra / producto**, no la OC completa.

Modelo conceptual:

```
PAÍS
  └── OC
       └── LÍNEA / SKU
            ├── proveedor
            ├── cantidad
            ├── valor
            ├── estado origen
            ├── transporte
            ├── fechas logísticas
            └── documentos
```

La UI puede agrupar por OC, pero los cálculos deben hacerse desde las líneas.

### 2.3 Evidencia del snapshot analizado

Snapshot recibido: `INFORME COMPRAS 2024-2026.xlsx`.

Filas sustantivas observadas:

| País | Líneas | OCs válidas por país |
|---|---:|---:|
| CO | 2.084 | 634 |
| EC | 76 | 32 |
| CL | 99 | 39 |
| **Total** | **2.259** | **705** |

Una OC puede contener más de un proveedor, estado o modo de transporte:

| Caso | OCs observadas |
|---|---:|
| Más de un proveedor | 214 |
| Más de un estado | 32 |
| Más de un modo de transporte | 46 |

Por esto, **no** se debe asumir `OC -> un proveedor -> un estado -> un embarque`.

---

## 3. Identificador de una OC

La llave funcional candidata es:

```
(pais, numero_oc)
```

No usar únicamente `NUMERO OC` como identificador global.

Casos sin OC válida en el snapshot:

- CO: 85 líneas con `N/A` y 3 con OC vacía.
- CL: 15 líneas con `N/A`.
- EC: no se observaron líneas sin OC válida.

Estas líneas **no deben desaparecer**. Deben mantenerse como registros de fuente y quedar clasificadas como `OC_NO_IDENTIFICADA` hasta definir tratamiento de negocio.

---

## 4. Contrato funcional canónico

Los nombres siguientes son conceptos del módulo; la fuente puede usar encabezados distintos por país.

### 4.1 Identificación

| Campo canónico | Fuente |
|---|---|
| `pais` | hoja de origen: CO / EC / CL |
| `cliente` | `CLIENTE` |
| `descripcion` | `DESCRIPCION` |
| `sku` | `SKU` |
| `id_cotizacion` | `SOLICITUD COTIZACION ID COTIZACION` |
| `proveedor` | `PROVEEDOR` |
| `numero_factura_proveedor` | `NUMERO DE FACTURA` |
| `confirmacion_oc` | `CONFIRMACIÓN OC` |
| `numero_oc` | `NUMERO OC` |
| `tipo_negociacion` | `TIPO DE NEGOCIACION` |
| `comercial_asignado` | `COMERCIAL ASIGNADO` |
| `elaboro_oc` | `ELABORO OC` |

### 4.2 Producto y volumen

| Campo canónico | Fuente |
|---|---|
| `cantidad` | `QTY` |
| `unidad_comercial` | `UNIDAD COMERCIAL` |
| `unidad_comercial_nombre` | `NOMBRE UNIDAD COMERCIAL (auto)` |
| `ctn` | `CTN` |
| `peso_total_kg` | `PESO TOTAL (Kg)` |
| `cbm` | `CBM` / `CBM (auto)` según hoja |
| `largo_cm` | `LARGO (cm)` |
| `ancho_cm` | `ANCHO (cm)` |
| `alto_cm` | `ALTO (cm)` |

### 4.3 Valor financiero

| Campo canónico | Fuente |
|---|---|
| `costo_unitario_usd` | `COSTO COMPRA CHINA/VENTA A LATAM USD` |
| `valor_total_compra_usd` | `VALOR TOTAL COMPRA USD` |
| `valor_oci_ddp` | `VALOR OCI (DDP)` |
| `fecha_abono_compra` | `FECHA DE COMPRA EN CHINA (ABONO)` |
| `fecha_pago_total_compra` | `FECHA PAGO TOTAL EN CHINA` |
| `fecha_solicitud_pago_abono` | `FECHA SOLICITUD PAGO (abono)` |
| `motivo_demora_abono` | `MOTIVO DEMORA ABONO` |

Se implementan **dos familias descriptivas en paralelo**:

- costo de compra: `VALOR TOTAL COMPRA USD`;
- valor comercial DDP: `VALOR OCI (DDP)`.

La hoja derivada `Supply Chain` del snapshot analizado usa `SUM de VALOR OCI (DDP)` por `ESTADO`, por lo que la familia DDP permite reproducir/comparar la lectura actual. Sigue pendiente decidir cuál familia debe tener jerarquía ejecutiva y cuál corresponde a cada KPI corporativo.

### 4.4 Producción

| Campo canónico | Fuente |
|---|---|
| `production_time_dias_estimado` | `PRODUCTION TIME DAYS (ESTIMADO)` |
| `fecha_entrega_proveedor_estimada` | `FECHA ENTREGA PROV. ESTIMADA (auto)` |
| `fecha_fin_produccion` | `FECHA FINALIZACIÓN DE PRODUCCIÓN` |
| `fecha_ingreso_bodega_origen` | `FECHA INGRESO A BODEGA EN ORIGEN` |
| `dias_produccion_real` | `DÍAS DE PRODUCCIÓN REAL (auto)` |

### 4.5 Logística

| Campo canónico | Fuente |
|---|---|
| `modo_transporte` | `MODO TRANSPORTE` |
| `documento_transporte` | CO: `DOCUMENTO DE TRANSPORTE`; EC/CL: `DOC TRANSPORTE` |
| `certificado_origen` | `CERTIFICADO DE ORIGEN` |
| `fecha_cargue` | `FECHA CARGUE` |
| `etd` | `ETD` |
| `telex_bl` | `Telex/BL` / `Telex/BL (auto)` |
| `eta` | `ETA` (en la fuente puede venir con espacio inicial) |
| `nacionalizacion` | `NACIONALIZACION` |
| `fecha_entrega_bodega_destino` | cambia por país: Bogotá / Quito / Santiago |
| `factura_destino` | `FACTURA` |
| `estado_origen` | `ESTADO` / `ESTADO ` |

---

## 5. Catálogos observados

### 5.1 Modos de transporte observados

| Valor fuente | Líneas observadas |
|---|---:|
| MARITIMO | 2.025 |
| AEREO | 95 |
| CASILLERO | 86 |
| MUESTRA | 53 |

La hoja `PARÁMETROS` contiene los mismos cuatro valores.

La plataforma debe conservar el valor original y producir una versión normalizada para análisis.

### 5.2 Estados

Ver `docs/compras/ESTADOS_LOGISTICOS.md`.

---

## 6. Regla de normalización

Nunca sobrescribir el dato de fuente.

Cada dimensión normalizada debe conservar ambos valores:

```
estado_origen
estado_normalizado

modo_transporte_origen
modo_transporte_normalizado
```

La normalización puede resolver:

- mayúsculas/minúsculas;
- tildes;
- espacios;
- variantes ortográficas equivalentes.

No puede cambiar el significado de negocio sin una decisión explícita.

---

## 7. Dos dimensiones para el estado

La columna `ESTADO` mezcla dos tipos de información:

1. **etapa física/logística**, por ejemplo `EN PRODUCCION`, `ENVIADO A DESTINO`, `ENTREGADO`;
2. **situaciones operativas o excepciones**, por ejemplo `ANULADA`, `EN RECLAMACION`.

Por eso se propone separar la interpretación en:

```
etapa_logistica
situacion_operativa
```

Ejemplo conceptual:

```
estado_origen = "EN RECLAMACION"
etapa_logistica = POR_DEFINIR
situacion_operativa = RECLAMACION
```

Esta separación es una **propuesta de diseño funcional**, no una regla corporativa cerrada todavía.

---

## 8. KPIs: contrato antes de implementación

### 8.1 Familias monetarias ya implementadas

La plataforma expone dos familias monetarias descriptivas, calculadas a nivel de línea y con `Decimal`:

- `costo_compra` → `VALOR TOTAL COMPRA USD`;
- `valor_comercial_ddp` → `VALOR OCI (DDP)`.

Para reproducir la población del pivote `Supply Chain` actual, ambas familias pueden calcular el total sobre estos estados fuente:

- `EN BODEGA ASIATI SHENZHEN`;
- `EN BODEGA ASIATI YIWU`;
- `EN NACIONALIZACION`;
- `EN OTM`;
- `EN PRODUCCION`;
- `ENVIADO A DESTINO`;
- `PENDIENTE DEPOSITO`.

Esto no asigna una etapa logística definitiva a `EN OTM` o `PENDIENTE DEPOSITO`.

Ver `docs/compras/KPIS_MONETARIOS.md`.

### 8.2 KPIs corporativos pendientes

Ningún KPI corporativo se implementa solo por el nombre.

Cada KPI debe documentar:

- pregunta que responde;
- nivel de granularidad;
- población incluida;
- estados incluidos/excluidos;
- columna monetaria;
- tratamiento de OC parcial;
- tratamiento de `N/A`;
- nulos;
- fórmula;
- ejemplo real de aceptación.

KPIs candidatos:

- valor de compras activas;
- valor en producción;
- valor en origen;
- valor en tránsito;
- valor en destino;
- valor en nacionalización;
- valor recibido;
- órdenes activas;
- ETA vencidas;
- próximas llegadas.

---

## 9. Puntos de atención

### 9.1 Observaciones objetivas implementadas

La plataforma ya puede señalar, sin asignar severidad de negocio:

- `ENVIADO A DESTINO` sin documento de transporte;
- `ENVIADO A DESTINO` sin ETD;
- `ENVIADO A DESTINO` sin ETA;
- ETA vencida sin entrega registrada;
- ETA no interpretable;
- fecha de entrega presente con etapa todavía abierta;
- OC con varios estados;
- OC con varios proveedores;
- OC con varios modos de transporte.

Estas reglas son observacionales: no corrigen la fuente ni concluyen por sí solas que exista un error de negocio.

### 9.2 Alertas todavía pendientes de definición

Siguen pendientes, entre otras:

- OC parcialmente recibida como alerta corporativa;
- producción por encima del tiempo esperado;
- pago/abono pendiente con operación en etapa avanzada;
- severidades, tolerancias y SLA.

Ver `docs/compras/DASHBOARD_EJECUTIVO.md`.

---

## 10. Hojas derivadas

Hojas como:

- `REPORTE OC`
- `Supply Chain`
- `Supply Chain Wiilog`
- `OPERACION X CLIENTE (CO)`
- `INFORME CORP`
- `INFORME E-COMM`
- `RESUMEN`
- `KPIs`
- `Calc_Data`
- `Dashboard_Final`

sirven para entender y validar el proceso actual.

No se consideran automáticamente fuente primaria.

Principio:

```
detalle fuente -> regla propia -> resultado -> comparación contra vista existente
```

---

## 11. Fuera de alcance por ahora

- reemplazar Google Sheets;
- escribir de vuelta al Sheet (prohibido por la decisión 0005 mientras siga vigente);
- construir base de datos propia de compras;
- OCR de comprobantes;
- reglas de cartera de clientes;
- UI definitiva;
- decidir por cuenta propia valores financieros o estados ambiguos.

---

## 12. Vertical slice técnico permitido antes de cerrar KPIs

Sí se permite implementar la **capa de lectura y normalización** antes de cerrar los KPIs, siempre que:

- use exclusivamente Google Sheets API en modo `spreadsheets.readonly`;
- no escriba ni corrija la fuente;
- conserve `estado_origen` y demás valores originales;
- clasifique solo estados de baja ambigüedad;
- deje `EN OTM`, `PENDIENTE DEPÓSITO`, `PENDIENTE INVIMA` y otros estados abiertos como `POR_DEFINIR`;
- no calcule todavía "valor en tránsito", pagado, saldo pendiente u otros KPIs con criterio financiero abierto.

Endpoints técnicos de solo lectura:

- `GET /api/v1/compras/fuente/estado`
- `GET /api/v1/compras/catalogos`
- `GET /api/v1/compras/calidad`
- `GET /api/v1/compras/resumen`
- `GET /api/v1/compras/kpis`
- `GET /api/v1/compras/dashboard`
- `GET /api/v1/compras/atencion`
- `GET /api/v1/compras/validacion/tablero`
- `GET /api/v1/compras/export.zip`
- `GET /api/v1/compras/ocs`
- `GET /api/v1/compras/lineas`

Todos requieren `compras.ver`.

La fuente usa un snapshot en memoria con TTL configurable mediante `COMPRAS_SHEETS_CACHE_SECONDS`. El cache existe únicamente para reducir lecturas repetitivas contra Google Sheets; no es una nueva fuente de verdad ni una base de datos.

Si desaparece un encabezado crítico o aparecen encabezados duplicados, la plataforma mantiene disponible el diagnóstico pero bloquea los endpoints operativos para evitar resultados silenciosamente incorrectos.

Ver `docs/compras/CONTRATO_FUENTE.md`.

### Criterio para comenzar lógica financiera / KPIs

Antes del primer PR que calcule KPIs financieros de Compras deben existir:

1. mapa validado de estados;
2. definición de al menos un KPI;
3. criterio de aceptación con filas reales;
4. tratamiento definido de OCs parciales;
5. tratamiento de líneas sin OC;
6. fuente/rango exacto de Google Sheets;
7. preguntas de negocio bloqueantes resueltas o marcadas como `TODO(negocio)`.

---

## 13. Explorador técnico antes del dashboard financiero

Se permite una vista exploratoria protegida de Compras antes de cerrar los KPIs financieros.

Esta vista puede:

- mostrar estado técnico de la fuente;
- mostrar filas leídas por hoja;
- mostrar drift de encabezados;
- listar OCs agrupadas sin asignar un único estado agregado;
- mostrar proveedores, estados, etapas y transportes observados por OC;
- abrir las líneas reales de una OC;
- mostrar observaciones de calidad;
- mostrar catálogos observados.

Esta vista **no es el dashboard financiero definitivo**.

Sí puede mostrar las dos familias monetarias descriptivas ya definidas —costo de compra y valor comercial DDP— y su desglose por estados del pivote actual. Esos totales deben etiquetarse como familias descriptivas, no como “valor en tránsito / en el mar” ni como KPI ejecutivo oficial hasta que negocio cierre esas definiciones.

Los valores monetarios de una línea siguen disponibles como evidencia cruda de fuente.


---

## 14. Vista ejecutiva descriptiva y validación

Existe una primera vista ejecutiva read-only para revisión de producto.

Puede mostrar:

- costo de compra de la población actual;
- valor comercial DDP de la población actual;
- OCs con al menos una línea en esa población;
- observaciones objetivas;
- distribución por estado y modo de transporte;
- comparación DDP por estado contra la hoja derivada `Supply Chain`;
- exportación de líneas, OCs, puntos de atención y KPIs en CSV dentro de un ZIP.

La validación contra `Supply Chain` solo se ejecuta cuando el parser puede identificar país, `ESTADO` y la columna DDP sin adivinar. La hoja derivada sigue siendo referencia de regresión, no fuente primaria.

Ver `docs/compras/DASHBOARD_EJECUTIVO.md`.
