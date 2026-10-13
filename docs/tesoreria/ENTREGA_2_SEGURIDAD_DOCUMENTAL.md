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
