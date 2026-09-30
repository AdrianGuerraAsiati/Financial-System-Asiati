# Entorno de desarrollo en AWS Lightsail

Estado: 30-sep-2026.

## Objetivo

Mantener un entorno compartido de desarrollo de bajo costo mientras la plataforma
todavía está en construcción. Este entorno no se considera la arquitectura final de
producción.

## Instancia

- Servicio: Amazon Lightsail
- Región: `us-east-2` (Ohio)
- Instancia: `financial-system-asiati-dev`
- Bundle: `micro_3_0`
- Precio del bundle: US$7/mes
- CPU: 2 vCPU
- RAM: 1 GB
- Disco: 40 GB SSD
- Transferencia incluida: 2 TB/mes
- Sistema operativo: Amazon Linux 2023
- IP estática: `3.141.226.208`
- URL temporal de desarrollo: `https://3-141-226-208.sslip.io/`

La URL `sslip.io` es únicamente para desarrollo y permite a Caddy obtener TLS sin
esperar la configuración del dominio corporativo.

## Memoria

La instancia tiene 1 GB de RAM. Se configura un swap de 2 GB para evitar fallos durante
builds de Docker. Esto no sustituye RAM real; si PostgreSQL + API + Caddy empiezan a
presionar memoria o swap de forma sostenida, el siguiente paso es subir al bundle
Lightsail Small de 2 GB.

## Deploy

El workflow `.github/workflows/deploy-development.yml` se ejecuta después de un CI
verde en `main`.

Flujo:

1. GitHub checkout del commit exacto aprobado por CI.
2. Se crea un artefacto `tar.gz` sin `.git`, secretos, fixtures ni archivos de entorno.
3. GitHub obtiene credenciales AWS temporales mediante OIDC.
4. GitHub solicita a Lightsail una llave SSH temporal con
   `get-instance-access-details`.
5. El artefacto se copia directamente con `scp`.
6. La instancia verifica SHA-256.
7. Se preservan `.env.production` y `secrets/`.
8. Alembic se ejecuta hasta `head`.
9. Docker Compose reconstruye/actualiza el stack.
10. El deploy solo termina bien si `/ready` y `/health` responden por HTTPS.

No hay PAT, deploy key permanente ni clon Git en la instancia.

## Datos y secretos

Para este entorno de desarrollo, PostgreSQL/JWT/webhook usan secretos aleatorios locales
creados durante el bootstrap y guardados exclusivamente en
`/opt/financial-system/.env.production`.

La credencial real de Google Sheets no está en Git. Se añadirá fuera del repositorio
cuando activemos la integración.

## Escalamiento

El bundle puede cambiarse cuando el comportamiento real lo justifique:

- Micro: 1 GB — punto de entrada actual.
- Small: 2 GB — siguiente paso si la memoria resulta insuficiente.

No se debe aumentar el tamaño por anticipado; primero se revisa CPU, RAM, swap y tiempos
de respuesta del entorno real.
