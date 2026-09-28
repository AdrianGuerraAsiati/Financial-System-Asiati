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
2. Configurar dominio, contraseña de PostgreSQL y variables de Google Sheets.
3. Colocar el service account de Google en la ruta indicada por `GOOGLE_SERVICE_ACCOUNT_FILE`.
4. Apuntar el DNS del dominio al servidor.
5. Ejecutar `docker compose -f compose.production.yml up -d --build`.

## Backup

El servicio `backup` genera un `.sql.gz` por intervalo en el volumen `backup_data` y aplica retención local.

**Esto no satisface por sí solo el requisito de backup fuera del servidor.** Antes de producción debe definirse un destino externo y copiar/sincronizar los backups allí. No se fija proveedor hasta que ASIATI confirme esa decisión.

Para restaurar:

```sh
DATABASE_URL=... sh ops/restore_postgres.sh /ruta/backup.sql.gz
```
