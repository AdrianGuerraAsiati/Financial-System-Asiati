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

- `NO_CONFIGURADO`: faltan ID/rangos o la empresa no coincide;
- `ERROR`: existe configuración pero la lectura de al menos un rango falló;
- `DEGRADADO`: se pudieron leer los rangos pero falta un encabezado crítico o hay duplicados;
- `OK`: los tres contratos mínimos son legibles.

La respuesta incluye filas leídas por rango, campos críticos faltantes y encabezados duplicados.

## 4. Variables requeridas

```dotenv
CARTERA_SHEETS_EMPRESA_ID=1
CARTERA_SHEETS_SPREADSHEET_ID=<id>
CARTERA_SHEETS_RANGE=<rango-operaciones>
CARTERA_SHEETS_MORA_RANGE=<rango-mora>
CARTERA_SHEETS_PROYECCION_RANGE=<rango-proyeccion>
GOOGLE_IMPERSONATE_SERVICE_ACCOUNT=<service-account>
```

## 5. Situación actual

El código de Cartera ya tiene contratos, consultas, mora, proyección y flujo de comprobantes, pero la hoja real no quedó configurada en el repositorio porque faltan deliberadamente el spreadsheet ID y los tres rangos.

No se debe asumir que `INFORME COMPRAS 2024-2026` es la fuente de Cartera. Aunque comparte algunos encabezados, no contiene el contrato completo observado por el tablero anterior (por ejemplo `VALOR ANTICIPO`, `VALOR FINANCIADO` y `CARTERA`).

El siguiente hito es identificar/compartir la hoja real, configurar los tres rangos y ejecutar `/fuente/estado` antes de tocar reglas financieras.
