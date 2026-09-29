# Actualización de dashboard por cambios en Google Sheets

## Objetivo

Abrir o recargar `Inicio` no debe volver a leer Google Sheets. El dashboard consume el
último snapshot persistido en PostgreSQL y solo solicita una nueva captura cuando el
Google Sheet notifica un cambio.

Flujo:

```
edición(es) en Sheet
  -> webhook ligero
  -> source_refresh_states = PENDING
  -> 15 s sin cambios (máximo 60 s)
  -> un cliente del dashboard reclama el refresco
  -> una lectura de Google
  -> hash
  -> snapshot nuevo solo si cambió el contenido
  -> /dashboard/version cambia de snapshot_id
  -> Inicio reemplaza las tarjetas sin borrar los datos anteriores
```

## Protección contra ráfagas

- `GOOGLE_SHEETS_DEBOUNCE_SECONDS=15`: espera 15 segundos desde la última edición.
- `GOOGLE_SHEETS_MAX_WAIT_SECONDS=60`: si alguien edita continuamente, se permite un
  refresco como máximo cada 60 segundos.
- `source_refresh_states` tiene una fila por empresa + módulo.
- El claim usa bloqueo de fila; dos navegadores no ejecutan dos lecturas simultáneas.
- Los snapshots de Cartera y Compras ya son idempotentes por hash, por lo que una
  notificación sin cambio sustantivo no genera una nueva versión.

## Webhook

`POST /api/v1/integrations/google-sheets/changed`

Header:

```
X-ASIATI-Sheet-Secret: <GOOGLE_SHEETS_CHANGE_SECRET>
```

Body:

```json
{
  "modulo": "cartera",
  "empresa_id": 1,
  "spreadsheet_id": "...",
  "hoja": "MORA",
  "rango": "C12",
  "tipo_evento": "EDIT"
}
```

El endpoint **no lee Google**. Solo registra el evento y responde 202.

## Apps Script

El archivo `ops/google_sheets_change_hook.gs` debe agregarse al proyecto de Apps Script
asociado al spreadsheet.

Crear estas Script Properties:

- `ASIATI_WEBHOOK_URL`:
  `https://<dominio>/api/v1/integrations/google-sheets/changed`
- `ASIATI_WEBHOOK_SECRET`: mismo valor que `GOOGLE_SHEETS_CHANGE_SECRET`.
- `ASIATI_MODULE`: `cartera` o `compras`.
- `ASIATI_EMPRESA_ID`: id de la empresa en la plataforma.

Luego ejecutar una vez `asiatiInstallTriggers()`. Crea triggers instalables de edición
y cambio estructural. Una pegada de muchas celdas puede generar uno o varios eventos,
pero el backend los agrupa antes de leer.

## Comportamiento de UI

`GET /api/v1/dashboard/principal` lee PostgreSQL/snapshots.

La web consulta cada 10 segundos:

`GET /api/v1/dashboard/version?empresa_id=<id>`

La consulta es ligera. Puede devolver:

- `PENDING`: “Cambios detectados · esperando que termine la edición…”
- `REFRESHING`: “Actualizando fuente en segundo plano…”
- `ERROR`: conserva el snapshot anterior y muestra el fallo de actualización.
- `IDLE`: sin trabajo pendiente.

Solo cuando cambia el `snapshot_id`, la UI vuelve a pedir `/dashboard/principal`.

## Primer snapshot

Esta implementación no inventa datos si todavía no existe una captura. Antes de activar
el flujo automático, guardar una captura inicial desde los endpoints/pantallas existentes
de Cartera y Compras. Después de eso, F5 nunca necesita leer Google.

## Límite conocido

Los triggers de Apps Script cubren edición humana y cambios estructurales del spreadsheet.
Si en el futuro otra API modifica el archivo sin disparar esos triggers, deberá añadirse un
listener de Drive/Workspace o hacer que esa automatización invoque el mismo webhook.
