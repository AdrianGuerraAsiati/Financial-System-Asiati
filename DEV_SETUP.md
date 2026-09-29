# Desarrollo local — quick start

El entorno local está preparado para que una instalación limpia muestre la plataforma sin configurar secretos corporativos.

## Requisitos

- Git
- Docker Desktop o Docker Engine + Docker Compose v2

No necesitas Python ni PostgreSQL instalados en el host.

## Arranque rápido

```bash
git clone https://github.com/AdrianGuerraAsiati/Financial-System-Asiati.git
cd Financial-System-Asiati
docker compose up --build
```

Docker Compose ejecuta automáticamente, en este orden:

1. PostgreSQL;
2. `alembic upgrade head`;
3. bootstrap local idempotente;
4. API FastAPI.

El bootstrap crea, solo si hacen falta:

- empresa: `ASIATI Demo`;
- superadministrador: `admin@asiati.local`.

Abre:

```text
http://localhost:8000
```

Credenciales locales por defecto:

```text
Correo: admin@asiati.local
Contraseña: AsiatiDev2026!
```

Estas credenciales son **solo para desarrollo local**. Los puertos del compose de desarrollo están ligados a `127.0.0.1`.

## Qué se puede ver sin Google

Compras / Supply Chain arranca por defecto con:

```text
COMPRAS_DEMO_MODE=true
```

La vista muestra datos sintéticos suficientes para revisar:

- login y sesión;
- selector de empresa;
- módulo Compras;
- diagnóstico de fuente;
- OCs y líneas;
- OCs mixtas;
- calidad;
- catálogos;
- costo de compra;
- valor comercial DDP;
- desglose monetario por estado;
- puntos de atención;
- gráficos descriptivos por estado y transporte;
- validación contra un pivote Supply Chain sintético;
- exportación ZIP de CSVs.

La interfaz marca explícitamente la fuente como:

```text
OK · DEMO LOCAL
```

Los datos demo no salen del repo hacia Google y no contienen información operativa real.

Cartera no tiene una fuente demo equivalente; sus consultas requieren configurar sus rangos reales.

## Personalizar el usuario local

Docker Compose funciona sin crear `.env`, pero puedes copiar el ejemplo:

```bash
cp .env.example .env
```

y cambiar:

```dotenv
DEV_ADMIN_EMAIL=admin@asiati.local
DEV_ADMIN_NAME=Administrador local
DEV_ADMIN_PASSWORD=AsiatiDev2026!
DEV_EMPRESA_NOMBRE=ASIATI Demo
```

El bootstrap es idempotente: no recrea ni reemplaza usuarios existentes.

## Conectar el Google Sheet real de Compras

La integración es de **solo lectura**. El adaptador nunca escribe en el Sheet.

### Opción recomendada: ADC de usuario + impersonación keyless

Este flujo evita claves privadas permanentes de service accounts y funciona cuando la
organización tiene bloqueada su creación.

1. Habilita Google Sheets API e IAM Service Account Credentials API en el proyecto de Google Cloud.

2. La cuenta de usuario que hará desarrollo local debe poder impersonar la service account
con el rol `Service Account Token Creator`. Comparte el Sheet con esa service account como
**Lector**.

3. Crea ADC de usuario en el host:

```bash
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform
```

4. Copia el archivo de configuración:

```bash
cp .env.example .env
```

En Windows, configura la ruta host del ADC y la service account a impersonar:

```dotenv
COMPRAS_DEMO_MODE=false
COMPRAS_SHEETS_EMPRESA_ID=1
COMPRAS_SHEETS_SPREADSHEET_ID=<id-del-google-sheet>
COMPRAS_SHEETS_CO_RANGE="'INFORME CLIENTES (CO)'!A:BG"
COMPRAS_SHEETS_EC_RANGE="'INFORME CLIENTES (EC)'!A:BG"
COMPRAS_SHEETS_CL_RANGE="'INFORME CLIENTES (CL)'!A:BG"
COMPRAS_SHEETS_SUPPLY_CHAIN_RANGE="'Supply Chain '!A:Z"
GOOGLE_SERVICE_ACCOUNT_FILE=C:/Users/<usuario>/AppData/Roaming/gcloud/application_default_credentials.json
GOOGLE_IMPERSONATE_SERVICE_ACCOUNT=<service-account>@<proyecto>.iam.gserviceaccount.com
```

El nombre actual de la pestaña oficial `Supply Chain ` contiene un espacio final y debe
preservarse en el rango mientras la fuente mantenga ese nombre.

5. Levanta con el override de Google:

```bash
docker compose -f docker-compose.yml -f compose.google.yml up --build
```

El contenedor monta el ADC como archivo de credenciales fuente. Python obtiene credenciales
temporales de la service account mediante impersonación y limita el acceso final al scope:

```text
https://www.googleapis.com/auth/spreadsheets.readonly
```

### Compatibilidad con JSON de service account

Si una instalación autorizada sí utiliza un JSON de service account, puede mantener
`GOOGLE_IMPERSONATE_SERVICE_ACCOUNT` vacío y apuntar
`GOOGLE_SERVICE_ACCOUNT_FILE` al JSON. No se debe versionar ninguna credencial.

No existe write-back.

## Comandos útiles

Ver estado:

```bash
docker compose ps
```

Ver bootstrap y migraciones:

```bash
docker compose logs migrate bootstrap
```

Seguir logs de la API:

```bash
docker compose logs -f api
```

Detener:

```bash
docker compose down
```

Borrar también la base local y empezar limpio:

```bash
docker compose down -v
docker compose up --build
```

## Problemas frecuentes

### El puerto 5432 está ocupado

PostgreSQL también se publica en localhost para depuración. Si ya tienes PostgreSQL local, cambia o elimina esta línea en `docker-compose.yml`:

```text
127.0.0.1:5432:5432
```

La API no necesita que PostgreSQL esté publicado al host; se conecta por la red interna de Compose.

### El Google Sheet real devuelve error

Revisa:

- `COMPRAS_DEMO_MODE=false`;
- `COMPRAS_SHEETS_SPREADSHEET_ID`;
- que el Sheet esté compartido con el correo del service account;
- que `GOOGLE_SERVICE_ACCOUNT_FILE` exista;
- que hayas usado `compose.google.yml`.

### Quiero volver al demo

En `.env`:

```dotenv
COMPRAS_DEMO_MODE=true
```

y vuelve a levantar solo con:

```bash
docker compose up --build
```

## Seguridad

El compose local:

- usa `APP_ENV=development`;
- usa cookie no-Secure porque sirve por HTTP local;
- publica API y PostgreSQL solo en `127.0.0.1`;
- permite credenciales locales conocidas;
- jamás debe reutilizarse como configuración de producción.

Producción usa `compose.production.yml` y `SESSION_COOKIE_SECURE=true`.
