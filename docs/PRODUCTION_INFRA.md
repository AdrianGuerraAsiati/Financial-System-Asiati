# Infraestructura de producción

Estado documentado: 30-sep-2026.

## Arquitectura

```
Internet
  -> CloudFront (HTTPS)
  -> EC2 origin HTTP :80, permitido solo desde la red origin-facing de CloudFront
  -> Caddy
  -> FastAPI
  -> PostgreSQL local en Docker
```

El host se administra mediante AWS Systems Manager. No se abre SSH público.

## AWS

- Región: `us-east-2`
- EC2: `i-0aa49867c85421e59`, `t3.small`
- Elastic IP: `16.58.88.113`
- Security group: `sg-00d7300aaf155ea70`
- CloudFront distribution: `E2SSSNPF1QQN2S`
- CloudFront domain: `d16dsqj8dxmbnw.cloudfront.net`
- Bucket de backup externo: `financial-system-asiati-prod-backups-890876258895-us-east-2`
- Rol de runtime EC2: `financial-system-asiati-prod-ec2`
- Rol GitHub OIDC: `arn:aws:iam::890876258895:role/financial-system-asiati-github-deploy`

Los secretos de PostgreSQL, sesión y webhook de Google Sheets viven en AWS Secrets Manager y no se versionan.

## Deploy

El workflow `.github/workflows/deploy-production.yml` se dispara únicamente cuando
`CI` termina correctamente sobre `main`, o manualmente mediante
`workflow_dispatch`.

GitHub usa OIDC; no existen access keys AWS de larga duración en el repositorio.

El workflow envía un comando SSM a la instancia. En el host:

1. se actualiza el checkout a `origin/main`;
2. se ejecuta `ops/deploy_production.sh`;
3. PostgreSQL se levanta primero;
4. Alembic corre hasta `head`;
5. Docker Compose reconstruye y actualiza los servicios;
6. el despliegue solo termina bien si `/ready` y `/health` responden.

## Backups

El servicio Docker `backup` genera los dumps locales.

Además, un cron del host sincroniza el volumen de backups a S3 cada hora. El bucket:

- bloquea acceso público;
- usa cifrado S3;
- tiene versionado;
- conserva objetos actuales 45 días;
- conserva versiones anteriores 14 días.

## Google Sheets

La infraestructura está lista para el webhook, pero las fuentes de negocio requieren
configurar en el host:

- credencial real del service account;
- `CARTERA_SHEETS_EMPRESA_ID`;
- `CARTERA_SHEETS_SPREADSHEET_ID`;
- rangos de Cartera;
- `COMPRAS_SHEETS_EMPRESA_ID`;
- `COMPRAS_SHEETS_SPREADSHEET_ID`.

No subir credenciales al repositorio.

## Dominio corporativo

Mientras DNS corporativo no esté configurado, CloudFront entrega HTTPS mediante su
dominio propio. Para publicar `finanzas.asiati.com.co`, se debe emitir/validar un
certificado ACM en `us-east-1`, añadir el alias a CloudFront y crear el registro DNS
en el proveedor que administra `asiati.com.co`.
