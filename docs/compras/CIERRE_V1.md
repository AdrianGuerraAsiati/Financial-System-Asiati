# Cierre de Compras / Supply Chain V1

**Estado:** CERRADA  
**Fecha de cierre:** 29 de septiembre de 2026  
**Fuente operativa:** Google Sheets `INFORME COMPRAS 2024-2026`  
**Modo de integración:** solo lectura

## 1. Qué significa "V1 cerrada"

Cerrar Compras V1 no significa que todas las preguntas de negocio estén resueltas.

Significa que existe una versión estable y auditable que:

- lee la fuente viva sin escribir en ella;
- conserva granularidad por línea;
- detecta drift crítico de esquema;
- normaliza únicamente equivalencias técnicas seguras;
- mantiene estados ambiguos sin inventar clasificación;
- expone KPIs descriptivos ya sustentados por la fuente;
- permite explorar OCs y líneas;
- muestra cobertura y observaciones;
- compara contra `Supply Chain ` como control de regresión;
- conserva snapshots históricos auditables;
- ofrece trazabilidad logística y próximas ETA;
- tiene contrato protegido por tests;
- deja explícitos los conceptos que pertenecen a una V2 o requieren decisión de negocio.

## 2. Criterios de aceptación cumplidos

### Fuente e integración

- Google Sheets real validado desde Docker.
- ADC de usuario + impersonación de service account validada.
- Scope final: `spreadsheets.readonly`.
- Hojas operativas:
  - `INFORME CLIENTES (CO)`
  - `INFORME CLIENTES (EC)`
  - `INFORME CLIENTES (CL)`
- La pestaña `Supply Chain ` se consume respetando el espacio final.
- No existe write-back de Compras al Google Sheet.

### Población

Baseline validado el 29/09/2026:

| País | Líneas sustantivas |
|---|---:|
| CO | 2.084 |
| EC | 76 |
| CL | 99 |
| **Total** | **2.259** |

La unidad mínima permanece en línea/producto.

### Contrato y calidad técnica

- Drift crítico bloquea cálculos operativos.
- `CBM` duplicado de EC/CL no bloquea porque no se usa como campo canónico.
- Fórmulas arrastradas en columnas auxiliares no crean líneas falsas.
- Encabezados reales de entrega a Bogotá/Quito/Santiago están normalizados.
- Se conserva país, hoja y fila fuente para trazabilidad.

### KPIs descriptivos

La V1 soporta, sin convertirlos en KPI corporativo definitivo:

- costo de compra mediante `VALOR TOTAL COMPRA USD`;
- valor comercial DDP mediante `VALOR OCI (DDP)`;
- distribución por estado;
- distribución por modo de transporte;
- OCs presentes en la población actual;
- observaciones de atención.

No se denomina ninguno de estos valores como "valor en tránsito / en el mar" sin definición de negocio.

### Reconciliación

La comparación viva contra `Supply Chain ` quedó operativa mediante metadata real del pivote.

Baseline observado:

- 11 comparaciones;
- 10 `COINCIDE`;
- 1 `SOLO_DETALLE`;
- diferencia conocida: CL · `PENDIENTE DEPOSITO` · USD 3.450.

La V1 muestra la diferencia y no la corrige silenciosamente.

### Trazabilidad y auditoría

La V1 incluye:

- snapshots persistentes;
- hash SHA-256 de contenido;
- filas crudas sustantivas;
- filas normalizadas;
- diagnóstico y rangos;
- auditoría del guardado;
- cobertura de campos;
- timeline por línea de OC;
- próximas llegadas basadas en ETA interpretable;
- exportación ZIP;
- UI de consulta y control.

## 3. Contrato API V1

Todos los endpoints requieren `compras.ver`.

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
- `GET /api/v1/compras/cobertura`
- `GET /api/v1/compras/timeline`
- `GET /api/v1/compras/llegadas`
- `GET /api/v1/compras/snapshots`
- `POST /api/v1/compras/snapshots`

El POST de snapshots persiste evidencia dentro de la plataforma; no modifica Google Sheets.

## 4. Non-goals de V1

Quedan explícitamente fuera de Compras V1:

- cuentas por pagar a proveedores;
- monto efectivamente pagado a proveedor;
- saldo pendiente a proveedor;
- cash-flow de compras;
- conciliación de pagos a proveedor;
- OCR de pagos a proveedor;
- write-back al Google Sheet;
- definición corporativa de "valor en tránsito / en el mar";
- definición de OC parcial/cerrada;
- severidades/SLA de atrasos;
- normalización canónica del `CBM` ambiguo de EC/CL;
- conversión y tratamiento financiero definitivo de monedas de `REPORTE OC`.

## 5. Decisiones de negocio pendientes

No son bloqueantes para considerar V1 cerrada.

Continúan como `TODO(negocio)`:

1. significado definitivo de `EN OTM`;
2. significado definitivo de `PENDIENTE DEPOSITO`;
3. tratamiento de `PENDIENTE INVIMA`;
4. definición oficial de "valor en tránsito / en el mar";
5. familia monetaria oficial para ese KPI;
6. criterio de OC parcial/cerrada;
7. tolerancias para producción y ETA;
8. semántica contable de `FACTURA` destino;
9. fuente oficial de montos reales pagados a proveedor;
10. alcance/moneda de `REPORTE OC`;
11. CBM canónico de EC/CL.

## 6. Regla de mantenimiento después del cierre

Cambios posteriores en Compras deben clasificarse como uno de estos tipos:

- **fix V1:** corrige un defecto contra este contrato sin cambiar semántica;
- **compatibilidad de fuente:** adapta drift real preservando la semántica V1;
- **V1.x:** mejora UX, observabilidad o rendimiento sin introducir regla financiera nueva;
- **V2:** incorpora una nueva regla de negocio, una nueva fuente financiera o conceptos como cuentas por pagar/pagos de proveedor.

No reabrir estados ambiguos ni fórmulas financieras mediante inferencia técnica.

## 7. Evidencia relacionada

- `docs/compras/AUDITORIA_FUENTE_2026-09-29.md`
- `docs/compras/CONTRATO_FUENTE.md`
- `docs/compras/KPIS_MONETARIOS.md`
- `docs/compras/DASHBOARD_EJECUTIVO.md`
- `docs/compras/ESTADOS_LOGISTICOS.md`
- `docs/decisiones/0005-compras-google-sheets-solo-lectura.md`
- `tests/test_compras_v1_contract.py`

## 8. Resultado

**Compras / Supply Chain V1 queda cerrada como vertical read-only, trazable y auditable.**

El siguiente desarrollo funcional debe ocurrir fuera del alcance V1 o como corrección compatible con este contrato.
