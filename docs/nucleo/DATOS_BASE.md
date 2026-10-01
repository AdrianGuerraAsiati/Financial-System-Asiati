# Datos base del núcleo

Empresas, períodos y fuentes son datos maestros del núcleo. No se crean desde los motores.

El cargador idempotente se ejecuta con un JSON externo al repositorio:

```bash
python -m app.core.datos_base --archivo /ruta/segura/datos_base.json
```

El formato está documentado en `docs/nucleo/datos_base.example.json`.

## Comportamiento

- Crea una empresa si no existe otra con el mismo nombre exacto.
- Reutiliza la empresa si ya existe.
- Crea o reutiliza períodos por empresa y rango de fechas.
- Crea o reutiliza fuentes por empresa y nombre exacto.
- No cambia el estado de un período existente. Si el archivo pide un estado distinto, falla y exige usar el flujo auditable de cierre o reapertura.
- Si encuentra empresas o fuentes duplicadas con el mismo nombre exacto, falla para que el catálogo se corrija antes de continuar.

El archivo con nombres operativos reales se mantiene fuera de Git. No requiere migraciones porque usa las tablas `empresas`, `periodos` y `fuentes` existentes.

## Lectura para las pantallas

La UI consulta los catálogos por empresa con:

```text
GET /api/v1/periodos?empresa_id={id}
GET /api/v1/fuentes?empresa_id={id}
```

Ambos endpoints usan `conciliacion.ver`, incluyendo el alcance por empresas asignadas. Los motores siguen siendo responsables de sus catálogos de dominio y reglas de negocio, no de estos datos maestros.


## Desarrollo: carga operativa desde S3

El entorno de desarrollo puede cargar el archivo operativo sin versionarlo mediante el workflow manual:

`Load development Wallets base data`

El archivo se mantiene en el bucket privado de desarrollo:

`s3://financial-system-asiati-dev-data-890876258895/dev/wallets/config/datos_base.json`

Flujo:

1. preparar el JSON con el mismo contrato de `datos_base.example.json`;
2. subirlo al objeto privado de S3 anterior;
3. ejecutar manualmente el workflow `Load development Wallets base data`;
4. el workflow obtiene acceso temporal a Lightsail con OIDC, copia el archivo de forma transitoria al host y al contenedor de la API y ejecuta:
   `python -m app.core.datos_base --archivo /tmp/datos_base_wallets.json`;
5. tanto la copia del host como la del contenedor se eliminan al terminar.

El workflow solo imprime conteos de empresas, períodos y fuentes creados/reutilizados; no vuelca el contenido operativo del archivo al log.

El proceso conserva la semántica idempotente del cargador. Si encuentra duplicados exactos o un período existente con un estado distinto al solicitado, falla y no intenta corregirlo silenciosamente.
