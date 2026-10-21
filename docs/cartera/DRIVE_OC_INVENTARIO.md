# Integración documental de O.C. con Google Drive · Primera fase

## Alcance

Se incorpora al repositorio existente (no se crea otro servicio):

- Inventario recursivo de carpetas y archivos de Google Drive API v3 en modo `drive.metadata.readonly`.
- Paginación y límites para impedir ingestas parciales no observadas.
- Historial de versiones por `(drive_file_id, drive_version)` en PostgreSQL.
- Migración Alembic `0034_cartera_oc_drive`, sobre `0033_wallets_correccion`.
- Consulta protegida: `GET /api/v1/cartera/ocs/drive/inventario?limit=50&offset=0`.
- Vista administrativa: `/static/ocs_drive.html`. Su botón consulta PostgreSQL, **no** inicia sincronización.

El Drive es una fuente multiempresa. Cada documento entra con `empresa_id=NULL`,
estado `SIN_ASIGNAR`. No se le atribuye empresa por carpeta ni se calcula cartera
automáticamente. Hasta validar la asignación jurídica con Juanfe, **solo** los
roles con alcance global `cartera.ver` pueden consultar los nombres/enlaces
(documentos de diferentes empresas).

**No incluye** todavía lectura binaria/interpretación de PDFs, homologación del
archivo REPORTE OC, 72 negociaciones del prototipo, conciliación financiera,
recaudos, eventos logísticos ni sincronización periódica. Es el primer paso
seguro sobre `main`, no la importación íntegra de v0.4.

## Configuración en Lightsail

La plataforma ya utiliza PostgreSQL y monta un secreto de Google en
`/run/secrets/google_service_account` como `GOOGLE_APPLICATION_CREDENTIALS`
desde `compose.production.yml`. No guardar ni subir nuevas claves a Git.

1. Conceder acceso de **lector** a la carpeta de O.C. al correo de la identidad
   de servicio usada en el despliegue. Habilitar Drive API en el proyecto Google.
   Puede que la cuenta actual para Sheets no tenga permiso para esta carpeta.
2. Guardar `CARTERA_OC_DRIVE_FOLDER_ID` fuera de Git en variables del entorno de
   ejecución. Raíz facilitada por negocio:
   `<ID_CARPETA_CONFIGURADO_EN_LIGHTSAIL>`.
3. Aplicar las migraciones con el flujo habitual de despliegue. No usar SQL manual
   ni `create_all()`. Recrear el contenedor `api` mediante el despliegue habitual
   para que lea la variable nueva de `.env.production`.
4. **Con el código desplegado y antes de escribir en PostgreSQL**, verificar que
   la identidad de servicio usada realmente puede leer la carpeta raíz y listar
   sus hijos. El acceso de ChatGPT o de un usuario humano **no** sirve como prueba:

```bash
cd /opt/financial-system
docker compose --env-file .env.production -f compose.production.yml \
  exec api python -m app.motores.cartera_ocs.drive_sync --preflight
```

Debe responder `{"estado": "OK", "acceso": "SOLO_LECTURA"}`.
Un HTTP 403/404 implica revisar permisos de la identidad de servicio; no iniciar
la carga ni atribuir documentos manualmente por el nombre de la carpeta.

5. **Solo después del preflight OK**, lanzar la primera carga supervisada:

```bash
docker compose --env-file .env.production -f compose.production.yml \
  exec api python -m app.motores.cartera_ocs.drive_sync
```

6. Validar el conteo de archivos en la respuesta y consultar la bandeja de
`/static/ocs_drive.html` con un usuario global con permiso `cartera.ver`.
No confundir un inventario correcto con conciliación o saldo de cartera.

Se imprimen solo conteos, nunca nombres, tokens ni valores contractuales.
Una falla de Drive aborta la transacción de metadata; los documentos de
la carpeta origen **no se modifican**.

El proceso es manual y debe ejecutarse de forma **exclusiva** para evitar dos
sincronizaciones simultáneas. El índice conserva todas las versiones observadas;
no elimina filas cuando un archivo desaparece de Drive.

## Criterios de aceptación

- API sin sesión responde 401 por el núcleo.
- Usuario con permiso solo por empresa no puede consultar un inventario sin
  asignación jurídica (403).
- Permiso global `cartera.ver` permite consultar únicamente metadatos.
- Dos ejecuciones con igual versión no crean dos registros.
- Un archivo nuevo o una nueva revisión crea otro registro.
- Los PDFs no se publican desde la plataforma ni se hacen públicos en Drive.
- No se genera importe ni vencimiento a partir de nombres de archivo.

## Pendientes antes de llamar a este módulo operativo

- Validación por Juanfe de empresa jurídica y propietario de cada OC.
- Prueba de permisos de Google Drive desde Lightsail (no se heredan de ChatGPT).
- Ejecución real del primer inventario y conteos auditables.
- Especificación de extracción PDF, política de revisiones, asociación por número
  de OC y cotejo con la fuente financiera existente.
- Scheduler seguro con exclusión mutua, métricas, alertas y última ejecución.
- Integración de la vista en la navegación general, posterior a validación de acceso.

> Los artefactos experimentales v0.4 generados fuera del repositorio se
> consideran material de referencia y **no** reemplazan los módulos actuales
> de `cartera_ocs`.
