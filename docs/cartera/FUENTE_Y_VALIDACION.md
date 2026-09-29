# Cartera — conexión y validación de fuente

**Estado:** preparación técnica lista; fuente real pendiente de identificación/configuración.  
**Modo:** Google Sheets, solo lectura.

## 1. Contratos heredados que ya existen

La plataforma conserva tres contratos derivados del tablero anterior de Cartera:

### Operaciones / Cartera en Camino

Rango configurable con `CARTERA_SHEETS_RANGE`.

Encabezados críticos mínimos para habilitar la lectura:

- `NUMERO OC`
- `VALOR OCI (DDP)`
- `CARTERA`

El normalizador existente también consume, cuando están disponibles:

- `NOMBRE`
- `CLIENTE`
- `DESCRIPCION`
- `SKU`
- `TIPO DE NEGOCIACION`
- `MODO TRANSPORTE`
- `DOCUMENTO DE TRANSPORTE`
- `ESTADO`
- `AÑO OC`
- `ETA`
- `ANTICIPO`
- `VALOR ANTICIPO`
- `VALOR FINANCIADO`

### Mora

Rango configurable con `CARTERA_SHEETS_MORA_RANGE`.

Encabezados críticos:

- `Cliente`
- `Monto en mora (USD)`
- `CARTERA`

También se consumen:

- `Empresa / Subtítulo`
- `Observación más reciente`

### Proyección

Rango configurable con `CARTERA_SHEETS_PROYECCION_RANGE`.

Encabezados críticos:

- `NUMERO OC`
- `FECHA DE PAGO ESPERADA`
- `MONTO ESPERADO`

El normalizador existente también consume cliente/contacto, producto, SKU, país, estado, documento de transporte, días, valor DDP y comercial.

## 2. Autenticación

Cartera usa el mismo patrón keyless validado en Compras:

1. ADC de usuario como credencial fuente;
2. `GOOGLE_IMPERSONATE_SERVICE_ACCOUNT` como principal objetivo;
3. credenciales temporales;
4. scope final exclusivo `spreadsheets.readonly`.

No existe write-back en el cliente de Cartera.

## 3. Diagnóstico de fuente

Endpoint protegido:

```
GET /api/v1/cartera/fuente/estado?empresa_id=<id>
```

Respuestas esperadas:

- `NO_CONFIGURADO`: faltan empresa/spreadsheet, la empresa no coincide o no hay ningún rango configurado;
- `ERROR`: un rango configurado no se pudo leer;
- `DEGRADADO`: existe al menos una configuración parcial, pero no están válidos los tres contratos;
- `OK`: Operaciones, Mora y Proyección están configurados y sus contratos mínimos son legibles.

Cada rango es independiente. Operaciones puede estar disponible aunque Mora o Proyección todavía no lo estén. La respuesta incluye `rangos_configurados`, `rangos_validos`, filas leídas, campos críticos faltantes, duplicados y configuración faltante por subfuente.

## 4. Descubrimiento de pestañas

Con empresa + spreadsheet configurados, no es necesario adivinar nombres de pestaña:

```
GET /api/v1/cartera/fuente/descubrir?empresa_id=<id>
```

El descubrimiento:

- lista las pestañas con Sheets API;
- inspecciona únicamente `A1:ZZ20` de cada una;
- busca los encabezados exactos de los contratos existentes;
- detecta encabezados aunque empiecen después de la fila 1;
- reporta coincidencias exactas y candidatos parciales;
- propone un rango A1 solo cuando todos los campos críticos coinciden;
- no modifica Google Sheets ni las variables de entorno.

La UI de Cartera expone este flujo con **Descubrir pestañas**.

## 5. Variables requeridas

Configuración global:

```dotenv
CARTERA_SHEETS_EMPRESA_ID=1
CARTERA_SHEETS_SPREADSHEET_ID=<id>
GOOGLE_IMPERSONATE_SERVICE_ACCOUNT=<service-account>
```

Rangos independientes; se pueden habilitar uno a uno:

```dotenv
CARTERA_SHEETS_RANGE=<rango-operaciones>
CARTERA_SHEETS_MORA_RANGE=<rango-mora>
CARTERA_SHEETS_PROYECCION_RANGE=<rango-proyeccion>
```

## 6. Calidad y precisión financiera

La API expone las cuatro validaciones heredadas mediante:

```
GET /api/v1/cartera/calidad?empresa_id=<id>
```

No se agregan severidades, scores ni reglas nuevas.

Los importes de Cartera usan `Decimal` en Python y se serializan como cadenas decimales en JSON. La UI los formatea sin convertirlos a `Number` de JavaScript.

## 7. Histórico auditable de fuente

La plataforma puede conservar capturas inmutables de la fuente sin escribir de vuelta al Sheet:

```
POST /api/v1/cartera/snapshots?empresa_id=<id>
GET  /api/v1/cartera/snapshots?empresa_id=<id>
```

Cada captura conserva:

- hash SHA-256 de contenido;
- rangos y diagnósticos;
- fila cruda;
- representación normalizada;
- conteos por Operaciones, Mora y Proyección;
- fecha de lectura y fecha de guardado.

La misma captura no se duplica para una empresa.

## 8. Situación actual

El código de Cartera ya tiene contratos, consultas, Mora, Proyección, calidad, comprobantes, diagnóstico, descubrimiento estructural y snapshots auditables. La fuente real sigue sin estar configurada porque el spreadsheet de Cartera/MAJO no está disponible con el acceso actual.

No se debe asumir que `INFORME COMPRAS 2024-2026` es la fuente de Cartera. Aunque comparte algunos encabezados, no contiene el contrato histórico completo.

El siguiente hito externo es obtener el **spreadsheet ID real** y acceso de lectura. Con solo ese dato se puede ejecutar `/fuente/descubrir`, identificar los rangos por contrato y habilitarlos uno a uno. No es necesario esperar los tres rangos para empezar la validación viva.
