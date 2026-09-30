# Despliegue base · Bloque 1

Esta configuración prepara una instalación de un solo servidor para la primera versión web.

## Incluye

- API FastAPI;
- PostgreSQL 16;
- Caddy como reverse proxy;
- HTTPS automático cuando el DNS de `ASIATI_DOMAIN` apunte al servidor;
- volumen persistente para comprobantes;
- backup diario de PostgreSQL;
- script de restauración;
- credencial de Google montada como secret de Docker Compose.

## Arranque

1. Copiar `.env.production.example` a `.env.production`.
2. Configurar dominio, contraseña de PostgreSQL, variables de Google Sheets y
   `JWT_SECRET` (aleatorio, 48+ caracteres; por ejemplo
   `python -c "import secrets; print(secrets.token_urlsafe(48))"`).
3. Colocar el service account de Google en la ruta indicada por `GOOGLE_SERVICE_ACCOUNT_FILE`.
4. Apuntar el DNS del dominio al servidor.
5. Para un arranque manual, ejecutar `bash ops/deploy_production.sh`. El script usa explícitamente `--env-file .env.production`, ejecuta Alembic y valida `/ready` y `/health`.
6. Crear el primer superadministrador desde la terminal (no hay endpoint público):
   `docker compose --env-file .env.production -f compose.production.yml exec api python -m app.core.usuarios.crear_superadmin --email <correo> --nombre "<nombre>"`.

La excepción temporal de la decisión 0004 ya fue cerrada: Cartera y Wiilog están detrás del modelo común de autenticación/autorización. Antes de publicar, mantener HTTPS, `SESSION_COOKIE_SECURE=true` y completar los controles operativos de producción descritos en este documento.

## Backup

El servicio `backup` genera un `.sql.gz` por intervalo en el volumen `backup_data` y aplica retención local.

**Esto no satisface por sí solo el requisito de backup fuera del servidor.** Antes de producción debe definirse un destino externo y copiar/sincronizar los backups allí. No se fija proveedor hasta que ASIATI confirme esa decisión.

Para restaurar:

```sh
DATABASE_URL=... sh ops/restore_postgres.sh /ruta/backup.sql.gz
```


## Sesión en producción

En producción, `SESSION_COOKIE_SECURE=true` es obligatorio y el acceso debe hacerse exclusivamente por HTTPS. En desarrollo local puede usarse `false` para `http://127.0.0.1`, pero ese valor no debe desplegarse en producción.

## Sincronización por cambios de Google Sheets

Generar un secreto independiente para `GOOGLE_SHEETS_CHANGE_SECRET` y configurarlo
también como `ASIATI_WEBHOOK_SECRET` en las Script Properties de cada spreadsheet.
El procedimiento de instalación del trigger está en
`docs/GOOGLE_SHEETS_EVENT_REFRESH.md`.

Antes de activar el trigger debe existir al menos un snapshot inicial de cada módulo que
se quiera mostrar en Inicio. El webhook no recalcula en cada edición: registra el cambio,
aplica debounce y conserva el último snapshot válido durante la actualización.


## Despliegue automático desde main

Producción se despliega mediante `.github/workflows/deploy-production.yml` después de
que `CI` termina correctamente sobre `main`. GitHub obtiene credenciales AWS efímeras
por OIDC y ejecuta el despliegue en la instancia mediante SSM; no se usa SSH ni access
keys persistentes.

El comando de producción es `bash ops/deploy_production.sh`. El script exige
`.env.production`, ejecuta `alembic upgrade head`, reconstruye los contenedores y
falla si `/ready` o `/health` no responden.

Detalles de la infraestructura: `docs/PRODUCTION_INFRA.md`.
