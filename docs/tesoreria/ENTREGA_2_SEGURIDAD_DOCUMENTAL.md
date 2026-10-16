# Entrega 2 — Seguridad documental de Tesorería (desarrollo)

## Alcance

La base PostgreSQL conserva las referencias de facturas y pagos; el volumen privado Docker tesoreria_data contiene PDF, XML e imágenes. El respaldo PostgreSQL anterior NO incluye estos archivos.

El workflow .github/workflows/backup-tesoreria-docs.yml programa un respaldo diario a las 03:17 UTC y admite ejecución manual. Se conecta por SSH temporal a Lightsail, empaqueta el volumen de Tesorería sin modificarlo, valida los hashes de todos los documentos y remite una copia comprimida a S3 bajo dev/tesoreria/backups/. Nunca incorpora información real al repositorio.

El backup es cifrado mediante SSE-S3 (AES256), con manifiesto JSON por ejecución (SHA-256, tamaño, fecha y commit, sin nombres de proveedores). El upload comprueba tamaño y checksum en metadatos S3. Los nombres de objetos son únicos. La expiración propuesta es de 45 días por política de ciclo de vida LIMITADA al prefijo de Tesorería. El rol de GitHub no necesita DeleteObject.

El script ops/tesoreria_archivos.py verifica nombres y hashes, rechaza enlaces, miembros de tar ajenos al contrato, duplicados, rutas fuera del directorio y archivos excesivos. Los archivos en tránsito .carga-* se excluyen al no existir todavía una referencia persistida. La escritura operativa se ha fortalecido: publicación atómica, fsync y modo 0600, sin sobrescritura.

## Prerrequisitos antes de declarar backups operativos

1. Añadir la política IAM ops/aws/tesoreria-dev-backup-role-policy.json al rol existente financial-system-asiati-github-deploy como política INDEPENDIENTE; nunca reemplazar su política deploy-lightsail.
2. Activar la regla de ciclo de vida ops/aws/tesoreria-dev-backup-lifecycle.json tras confirmar que no se pisan reglas existentes. El bucket de desarrollo ya tenía cifrado SSE-S3 y bloqueo público; no tenía versioning ni lifecycle durante la revisión.
3. Fusionar código y desplegar a desarrollo para que el servidor disponga del script de archivado.
4. En una validación posterior, disparar el workflow manualmente y comprobar archivo .tar.gz y manifiesto .json, permisos privados, cifrado y checksum coincidente.
5. Programar alertas de ausencia/fallo de respaldos y ejecutar recuperación controlada cuando Finanzas autorice una muestra real.

## Incidencia de SSH y validación pendiente (16-oct-2026)

Los backups automáticos del **15 y 16 de octubre de 2026** terminaron en
`failure`. En el [run #38846487682](https://github.com/AdrianGuerraAsiati/Financial-System-Asiati/actions/runs/38846487682)
del 16-oct, el acceso temporal de AWS se obtuvo, pero SSH respondió
`Permission denied (publickey,...)` **antes** de generar el archivo comprimido.

El workflow de despliegue (que había terminado correctamente) lee
`accessDetails.certKey` y guarda el certificado de usuario junto a la
clave SSH temporal; el workflow de respaldo solo guardaba la clave.
La corrección propuesta replica la configuración de certificado opcional,
lo valida antes de usarlo y elimina ambos archivos al terminar. La
explicación es coherente con el síntoma, pero **solo una ejecución real
posterior al merge podrá confirmar que lo corrige**.

### Procedimiento para comprobar el respaldo después del fix

1. Revisar las pruebas del PR y fusionarlo en `main` sin modificar las
   facturas. El workflow tiene `workflow_dispatch` (manual) y horario
   diario; **no** corre en pull requests.
2. En GitHub Actions → `Backup Tesoreria documents (development)` →
   **Run workflow** (rama `main`). Asegurar que la cuenta y el rol AWS
   correspondan a ASIATI; no publicar archivos ni credenciales en logs.
3. Exigir resultado `success` con comprobación de conectividad SSH y
   generación/validación del tar, y consultar en almacenamiento privado S3
   la existencia del archivo y manifiesto bajo `dev/tesoreria/backups/`.
4. Validar en S3 tamaño, SHA256 del metadato, cifrado AES256, acceso
   restringido y consistencia del manifiesto. Registrar únicamente
   hora, identificador del run, estado y referencias privadas.
5. Si falla **después** del acceso SSH, tratar ese error como incidencia
   nueva (permisos IAM/S3, ruta/volumen, archivos corruptos). No informar
   backup exitoso solo porque SSH conecte.
6. La restauración controlada y la comprobación de correspondencia con
   PostgreSQL requieren gate y autorización separados: nunca restaurar
   automáticamente ni escribir sobre el volumen activo.

**Estado a 16-oct:** acceso al servidor y verificación S3 no completados.
Ninguna copia verificada de esa fecha queda acreditada por estos runs.

## Recuperación (procedimiento para uso futuro)

No se restaura automáticamente ningún archivo ni se escribe jamás en el volumen activo. La extracción exige ruta ABSOLUTA vacía cuyo último componente empiece por tesoreria-restore-; nunca usa extracción de tar sin validación. En una máquina de administración autorizada:

1. Con AWS CLI y una identidad con permiso de lectura específico, bajar el objeto .tar.gz y su .json del mismo nombre base al directorio privado de trabajo.
2. Leer el campo sha256 del manifiesto y verificar el archivo completo con: python3 ops/tesoreria_archivos.py verificar --archive /ruta/backup.tar.gz --sha256 SHA_DE_MANIFIESTO.
3. Extraer a un directorio temporal aislado, no existente: python3 ops/tesoreria_archivos.py restaurar --archive /ruta/backup.tar.gz --sha256 SHA_DE_MANIFIESTO --dest /tmp/tesoreria-restore-controlada.
4. Comparar con las referencias y fecha del respaldo PostgreSQL correspondiente, sin copiar todavía ningún archivo al volumen vivo.
5. Solo ante una contingencia y con procedimiento aprobado de suspensión/replicación, TI y el área financiera pueden decidir restaurar datos y adjuntar evidencia auditada de la actuación.

## Restricciones expresas

- Esta política NO respalda PostgreSQL, Cartera ni Compras; deben mantenerse sus sistemas propios de backup.
- No se mezclan monedas, no se modifican saldos, pagos, catálogos ni fechas; tampoco se habilitan listas nuevas de cuenta o ciudad sin fuentes autorizadas.
- El respaldo de PostgreSQL y el de documentos son independientes y tienen distintas retenciones; no es legítimo asegurar recuperación punto-en-tiempo consistente sin alinear ambos.
- Sin pruebas de recuperación reales no se promete RPO/RTO ni aceptación de negocio.
- Por ahora hay archivo COMPLETO cada día, no copia incremental. Revisar costos y ventana operativa cuando crezca el volumen.
- Esta automatización pertenece SOLO a desarrollo; producción requiere privilegios IAM y operación de recuperación separados.
