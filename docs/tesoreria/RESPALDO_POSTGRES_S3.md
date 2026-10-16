# Prioridad 1 — Respaldo PostgreSQL fuera de Lightsail (desarrollo)

## Objetivo y límites

Conservar el respaldo local `backup_data` y añadir una **segunda copia externa cifrada** de **toda la base de datos PostgreSQL** en S3 (incluye datos de módulos distintos de Tesorería). Los documentos PDF/XML/imagen continúan en un respaldo **independiente** bajo `dev/tesoreria/backups/`; este trabajo no cambia la base, los pagos ni los saldos.

- Copia local: `ops/backup_postgres.sh` y `ops/backup_loop.sh` mantienen retención de 14 días en el volumen Docker `backup_data`. `bash` habilita `pipefail` para detectar fallos de `pg_dump` aunque `gzip` termine correctamente; publicación sin reemplazo y verificación `gzip -t` + marcador final de PostgreSQL. Si falla, no publica un backup parcial ni elimina copias anteriores.
- Copia externa: `.github/workflows/backup-postgres-offsite.yml` por `workflow_dispatch` o cron `02:47 UTC`, SSH efímero de Lightsail + OIDC AWS. Extrae el dump con `pg_dump` desde el contenedor PostgreSQL sin detener servicios, comprime por streaming y **nunca imprime SQL en logs**. El runner valida el gzip y el marcador de fin antes de escribir en S3.
- S3: `s3://financial-system-asiati-dev-data-890876258895/dev/postgres/backups/`; archivo `.sql.gz` y manifiesto `.json` con tamaño, SHA-256, fecha UTC, formato, origen y commit. Ambos con `--sse AES256`; tras la subida se consultan los encabezados S3 para comprobar tamaño, SHA-256 en metadata y cifrado.
- Nunca adjuntar el dump a un PR, artefacto de GitHub Actions ni repositorio público. Contiene información sensible de **toda** la plataforma.

## Preparación IAM: pendiente hasta que se apruebe el PR

La cuenta objetivo es `890876258895` (región `us-east-2`). El rol OIDC `financial-system-asiati-github-deploy` dispone de `deploy-lightsail` y `tesoreria-dev-backup`, pero **aún no tiene autorizaciones en `dev/postgres/backups/`**. Instalar `ops/aws/postgres-dev-backup-role-policy.json` como una **política inline independiente** llamada `postgres-dev-backup`, conservando las demás. No otorgar lectura ni escritura sobre otros prefijos; no otorgar `DeleteObject` ni hacer público el bucket. Confirmar con IAM antes de ejecutar.

**Importante:** el bucket ya tiene una regla de expiración de 45 días para `dev/tesoreria/backups/`. Si se decide agregar retención para PostgreSQL (propuesta: 45 días en desarrollo), hay que **leer y fusionar** la configuración actual de lifecycle antes de aplicar una nueva. `PutBucketLifecycleConfiguration` reemplaza el conjunto completo de reglas: jamás sustituir la de documentos por accidente. La creación de esta nueva regla no forma parte del PR.

## Gate de operación

1. Revisar y fusionar el PR con unitarios, integración y auditoría en verde. Confirmar que el servicio local de respaldo sigue activo con la imagen y el script corregido.
2. Instalar la política IAM específica y comprobar permisos efectivos sin modificar las políticas existentes.
3. Ejecutar `Backup PostgreSQL offsite (development)` en la rama `main` desde GitHub Actions. No subir credenciales ni el archivo al chat o al repositorio.
4. Comprobar el `success` del job. En AWS/S3 comprobar existencia de `.sql.gz` y `.json`, SHA-256 del archivo comparado con el manifiesto y metadata, tamaño y `AES256`. La comparación de headers que realiza el job no es una lectura independiente de contenido; para aceptación, descargar en un entorno privado y calcular nuevamente SHA-256.
5. Probar recuperación **solo sobre una base de datos aislada y desechable**, sin apuntar a ninguna instancia viva. Validar tablas y una muestra sintética/permitida; guardar solo evidencia no sensible. Un dump válido no garantiza restauración hasta ejecutar este ensayo.
6. Verificar la paridad de los respaldos de documentos y PostgreSQL; no afirmar consistencia punto-en-tiempo, ni RPO/RTO contractual, por tratarse de procesos separados.

## Criterio de salida

Un run verde, objeto presente, metadatos coherentes y cifrado demuestran una copia **técnicamente transferida**. La capacidad de recuperación integral requiere una **restauración comprobada** en entorno aislado y asociar documentos y registros con cortes compatibles.
