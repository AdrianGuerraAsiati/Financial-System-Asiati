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

## Órdenes y soportes dentro de Cartera

La sección **«Órdenes y soportes · Google Drive»** está integrada al módulo Cartera.
No depende de que la fuente Google Sheets de operaciones, mora o proyección esté
disponible. Consulta **PostgreSQL**, no Google Drive en vivo.

APIs bajo `/api/v1`:

- `GET /cartera/ocs/drive/ordenes?buscar=GM607&limit=30&offset=0`:
  lista OC **candidatas** por coincidencia inequívoca de referencia GM en el
  nombre del documento, agrupa por OC y pagina grupos, no archivos.
- `GET /cartera/ocs/drive/ordenes/GM607/soportes`:
  presenta la última revisión indexada por ID de archivo, con enlace original.
- `GET /cartera/ocs/drive/inventario`:
  conserva el inventario administrativo plano y todo el histórico.

**Seguridad:** los documentos todavía no están asociados jurídicamente a una
empresa; los dos endpoints nuevos solo permiten roles con alcance global
`cartera.ver`. El panel se oculta para perfiles limitados a empresas, pero
la seguridad efectiva está en FastAPI (403). Los enlaces originales exigen
que el usuario tenga permisos en Google Drive; no se exponen contenidos PDF
desde ASIATI.

**Límites:** no se infiere la empresa por carpeta, nombre de cliente o
selección actual del usuario. No se calculan saldos, conciliaciones, vencimientos
ni resultados a partir del PDF o sus metadatos. Si un documento no contiene una
referencia GM válida en el nombre, queda contabilizado como
`archivos_sin_oc` y disponible en el inventario global, sin imputación forzada.
No se sincroniza al pulsar `Consultar índice`: la carga real se hace desde
Lightsail según la sección anterior.

### Aceptación del hito de visibilidad

1. PR de vista aprobado con CI unit/integration/security en verde.
2. Carpeta raíz configurada en el contenedor y preflight real exitoso.
3. Primer inventario supervisado, con conteos no nulos comprobados.
4. Vista de Cartera para administrador global muestra GM y soportes sin
   duplicar versiones de un mismo archivo; usuario de empresa recibe 403.
5. Evidencia de al menos dos OC reales con enlaces de Drive comprobados
   por un usuario autorizado. Si no hay archivos indexados, la vista muestra
   estado vacío, no datos inventados.
6. Juanfe valida la atribución jurídica antes de habilitar consulta por empresa,
   asociación definitiva con órdenes financieras o cálculos de cartera.

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
