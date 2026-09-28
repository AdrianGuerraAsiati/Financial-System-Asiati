# ESPECIFICACIÓN DEL NÚCLEO — PLATAFORMA FINANCIERA ASIATI

> Para el desarrollador fullstack.
> Versión 1 · septiembre 2026
> **Este documento define únicamente el núcleo.** Los motores tienen sus propias especificaciones y las escribe Coordinación de Datos.

---

## §0 · QUÉ ES ESTO Y QUÉ NO

Estamos construyendo una plataforma de conciliación y reporte financiero para las seis líneas del holding. La plataforma es **un núcleo compartido con motores enchufados encima**.

**Tu alcance es el núcleo.** Lo que construyas no sabe nada de wallets, de bancos ni de órdenes de compra: sabe de usuarios, empresas, períodos, cargas de archivos, movimientos categorizados, hallazgos y auditoría.

**Fuera de tu alcance:** las reglas de negocio de cada motor. Esas llegan como paquetes que se enchufan al contrato de §5.

**Por qué importa la separación.** Un intento anterior de este proyecto se detuvo porque nadie era dueño de las piezas comunes y cada parte se armaba las suyas. El núcleo tiene un responsable con nombre — vos — y los motores tienen otro.

### El principio que gobierna todo

**El motor es la unidad de código; la empresa es un dato.**

Habrá un solo `conciliacion_wallets`, configurado para tres líneas de negocio distintas. Nunca tres carpetas. Si alguien propone copiar un motor para otra empresa, es un rechazo en revisión de código.

En la interfaz sí se navega por empresa — `WIILOG > Conciliación de wallets` — pero eso es una ruta y una fila de configuración, no una carpeta en el repositorio.

---

## §1 · STACK

```
Backend    Python 3.12 · FastAPI · SQLAlchemy 2.x · Alembic · Pydantic 2 · psycopg · pandas · openpyxl · pytest
Frontend   React 18 · TypeScript · Vite · React Router · TanStack Query · Axios · Tailwind · Recharts
Datos      PostgreSQL 16
Infra      Docker · Docker Compose · Nginx · AWS Lightsail (Ubuntu 24.04, 4 GB) · Cloudflare DNS · Certbot
```

**Sin Next.js:** no hay SEO ni público anónimo. Una SPA detrás de login es más simple de operar.

**Sin Redis, sin Celery, sin colas, sin Kubernetes.** Seis motores y un cierre mensual no lo justifican. Pero estructurá el procesamiento de cargas con una tabla `jobs` y estados, para que agregar una cola después sea un cambio local y no una reescritura.

**`NUMERIC(18,2)` para todo lo monetario. Nunca FLOAT.** Esto no es negociable: son cifras contables que se auditan.

---

## §2 · ESTRUCTURA DEL REPOSITORIO

```
/
├── backend/
│   ├── app/
│   │   ├── api/v1/           rutas del núcleo
│   │   ├── core/             config, seguridad, logging
│   │   ├── db/               sesión, base
│   │   ├── models/           SQLAlchemy del núcleo
│   │   ├── schemas/          Pydantic del núcleo
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── nucleo/
│   │   │   ├── ingesta/      parser, hash, validación genérica
│   │   │   ├── categorizador/ el motor de reglas de las 7 dimensiones
│   │   │   ├── hallazgos/
│   │   │   └── registro.py   ← el registro de motores
│   │   ├── motores/          ← una carpeta por motor, las llena el otro frente
│   │   │   └── conciliacion_wallets/
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── nucleo/           layout, auth, cargas, movimientos, hallazgos
│   │   ├── motores/          ← una carpeta por motor
│   │   └── registro.ts       ← el registro de rutas y componentes
│   ├── Dockerfile
│   └── vite.config.ts
├── nginx/default.conf
├── scripts/{setup-server.sh,deploy.sh,backup-db.sh,restore-db.sh}
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
└── README.md
```

Esta estructura y estos nombres **se fijan desde el día uno**. Renombrar después es lo que mata el impulso de un proyecto.

---

## §3 · MODELO DE DATOS DEL NÚCLEO

Un solo PostgreSQL. El núcleo vive en el esquema `public`; cada motor puede crear el suyo (`wallets`, `bancos`, `cartera`).

### Organización

```sql
empresas
  id, nombre, nit, activa, creado_at
  -- las seis líneas: ASIATI importaciones, Matriz China, Chin Chin,
  -- Wiilog, Origen Vital, Ecomworld

unidades_negocio
  id, empresa_id, nombre, activa
  -- las categorías que hoy viven en la columna UNID. NEGOCIO

fuentes
  id, empresa_id, motor_slug, nombre, tipo,
  empresa_default, modalidad_default, activa
  -- una fuente = "la wallet de Wiilog", "la cuenta Bancolombia 4386"
  -- motor_slug dice qué motor la procesa
```

### Períodos y cierres

```sql
periodos
  id, codigo,              -- '2026-09'
  estado,                  -- abierto | cerrado
  cerrado_por, cerrado_at
  UNIQUE (codigo)

cierres_motor
  id, periodo_id, motor_slug, fuente_id,
  estado,                  -- pendiente | ejecutado | cerrado
  score NUMERIC(5,2),
  parametros_version_id,
  ejecutado_at
  UNIQUE (periodo_id, motor_slug, fuente_id)
```

**Regla dura:** un período cerrado no se recalcula. Queda congelado con sus resultados y con la versión de parámetros que se usó. Reabrirlo es una acción de admin que se escribe en auditoría.

### Cargas

```sql
cargas
  id, periodo_id, fuente_id, motor_slug,
  tipo,                    -- lo declara el motor
  nombre_archivo,
  hash_sha256,             UNIQUE
  filas, rango_fecha_min, rango_fecha_max,
  estado,                  -- recibida | validada | bloqueada | procesada | fallida
  errores JSONB,
  cargado_por, cargado_at
```

**Idempotencia:** el mismo archivo cargado dos veces se reconoce por hash y se rechaza con un mensaje claro, sin duplicar nada. El índice UNIQUE es la defensa real contra condiciones de carrera, no el chequeo en código.

### Movimientos — la tabla central

Tiene **exactamente la forma de la hoja de cálculo que usa contabilidad hoy**, más campos de control. Así el export sale idéntico y nadie tiene que reaprender nada.

```sql
movimientos
  id, fuente_id, carga_id, periodo_id,

  -- las columnas de la hoja actual, en su orden
  fecha_pago_oportuno   DATE,
  fecha                 DATE NOT NULL,
  tipo                  TEXT NOT NULL,      -- INGRESO | EGRESO
  monto                 NUMERIC(18,2) NOT NULL,
  descripcion           TEXT NOT NULL,      -- texto crudo de la fuente
  ciudad                TEXT,
  unidad_negocio        TEXT,
  categoria             TEXT,
  empresa               TEXT,
  tercero               TEXT,
  modalidad             TEXT,
  fijo_variable         TEXT,
  recibo_pago_caja      TEXT,
  causacion             TEXT,

  -- control
  descripcion_norm      TEXT NOT NULL,      -- mayúsculas sin acentos
  estado_categoria      TEXT NOT NULL,      -- AUTO | REVISAR | PENDIENTE | MANUAL
  regla_id              BIGINT NULL,
  categorizado_por      BIGINT NULL,
  categorizado_at       TIMESTAMPTZ NULL,
  referencia_externa    TEXT NULL,          -- el motor la usa para cruzar
  hash_fila             TEXT NOT NULL,
  crudo                 JSONB NOT NULL,     -- la fila original, intacta

  UNIQUE (carga_id, hash_fila)
```

**Mes, año, número de mes y semana NO se guardan.** Hoy son fórmulas en la hoja; en base de datos se calculan al consultar. Guardarlas es duplicar estado que se desincroniza.

**`crudo` siempre se guarda.** Si mañana una regla cambia, se recalcula sin volver a pedir el archivo.

### El catálogo de reglas

```sql
reglas_categorizacion
  id, motor_slug, fuente_id NULL,   -- NULL = aplica a todas las fuentes del motor
  patron                TEXT NOT NULL,
  tipo_match            TEXT NOT NULL,  -- EXACTO | EMPIEZA_CON | CONTIENE | REGEX
  prioridad             INT NOT NULL,   -- menor gana
  condiciones           JSONB,          -- signo, rango de monto, contraparte

  -- lo que asigna
  tipo, ciudad, unidad_negocio, categoria, empresa,
  tercero, modalidad, fijo_variable,

  requiere_revision     BOOL NOT NULL DEFAULT false,
  activa                BOOL NOT NULL DEFAULT true,
  origen                TEXT,           -- IMPORTADA | MANUAL | APRENDIDA
  veces_aplicada        INT DEFAULT 0,
  creado_por, creado_at
```

### Hallazgos

```sql
resultados
  id, periodo_id, fuente_id, motor_slug,
  regla_codigo          TEXT,           -- 'C1', 'C4'... lo define el motor
  entidad_tipo          TEXT,           -- 'orden' | 'movimiento' | 'documento'
  entidad_id            TEXT,
  estado                TEXT,
  monto_en_juego        NUMERIC(18,2),
  detalle               JSONB
  UNIQUE (periodo_id, motor_slug, regla_codigo, entidad_tipo, entidad_id)

hallazgos
  id, resultado_id,
  estado                TEXT,   -- detectado | asignado | en_gestion | resuelto | cerrado
  severidad             TEXT,   -- critico | medio | informativo
  responsable_id        BIGINT NULL,
  justificacion         TEXT,
  justificacion_persistente BOOL DEFAULT false,
  creado_at, actualizado_at
```

**La regla de la memoria.** Cuando un hallazgo se justifica con `justificacion_persistente = true`, la justificación queda ligada a la entidad. En el cierre siguiente el motor lo vuelve a detectar, el núcleo encuentra la justificación y lo marca resuelto sin volver a levantarlo. Sin esto la bandeja crece para siempre y la gente deja de usarla.

### Parámetros, usuarios y auditoría

```sql
parametros_versiones
  id, motor_slug, fuente_id NULL, version INT,
  contenido JSONB, creado_por, creado_at
  UNIQUE (motor_slug, fuente_id, version)

usuarios
  id, email UNIQUE, nombre, password_hash, rol, activo, creado_at
  -- password_hash con Argon2

auditoria
  id, usuario_id, accion, entidad, entidad_id,
  antes JSONB, despues JSONB, ip, creado_at
```

**Los parámetros nunca se sobrescriben: se versionan.** Un cierre recalculado dos meses después tiene que usar los parámetros con los que se cerró, no los de hoy.

---

## §4 · EL CATEGORIZADOR

Esta es la pieza del núcleo que más valor entrega y la que hay que hacer bien.

### Qué reemplaza

Hoy alguien pega un extracto en una hoja, unas fórmulas normalizan fecha y monto, y un `VLOOKUP` contra un catálogo de ~1.578 descripciones trae las siete dimensiones. Lo que el `VLOOKUP` no encuentra se llena a mano.

Sobre 10.506 movimientos del histórico ese proceso deja categoría y unidad de negocio llenas al **99,6 %**. Ese número es tu piso: si el categorizador queda por debajo, es una regresión frente a la hoja.

### Cómo funciona

```
1. normalizar(descripcion) -> mayúsculas, sin acentos, espacios colapsados
2. buscar reglas activas del motor_slug (y de la fuente si las hay),
   ordenadas por prioridad ascendente
3. la primera que empareja gana
4. si requiere_revision -> estado REVISAR (propone pero no cierra)
   si no                -> estado AUTO
5. si ninguna empareja  -> estado PENDIENTE, las 7 dimensiones en NULL
6. guardar SIEMPRE regla_id, para poder auditar y recalcular
```

**Tres cosas que lo diferencian del `VLOOKUP`:**

1. **Match por patrón, no por igualdad.** Los conceptos de las fuentes son plantillas con cola variable — `SALIDA POR COBRO DE FLETE INICIAL` seguido del número de orden. Un match exacto falla apenas cambia el sufijo.

2. **Reglas ambiguas que piden confirmación.** Hay conceptos que el texto por sí solo no resuelve porque dependen del contexto. Esas reglas llevan `requiere_revision = true` y el movimiento queda en `REVISAR`.

3. **Aprendizaje.** Cuando alguien resuelve un movimiento `PENDIENTE`, la API devuelve una sugerencia de regla y el usuario decide si aplica solo a ese movimiento o a todos los futuros iguales. **La decisión es del usuario, nunca automática** — una regla mal inferida se propaga a todos los meses siguientes sin que nadie lo note.

### Recategorizar

`POST /reglas/{id}/reaplicar` recorre los movimientos del período abierto y aplica la regla. Nunca toca períodos cerrados.

---

## §5 · EL CONTRATO DEL MOTOR

Esto es lo que permite que dos personas construyan en paralelo sin abrir el mismo archivo.

```python
# backend/app/nucleo/registro.py

class ClaseMotor(str, Enum):
    CONCILIACION = "conciliacion"   # cruza contra un soporte, produce hallazgos
    REPORTE      = "reporte"        # solo lee lo ya categorizado

class Motor(Protocol):
    slug: str                       # "conciliacion_wallets"
    nombre: str                     # "Conciliación de wallets"
    clase: ClaseMotor
    fuentes_requeridas: list[str]

    def esquema_parametros(self) -> dict: ...

    # solo clase CONCILIACION
    def validar(self, carga: Carga, params: dict) -> ResultadoValidacion: ...
    def ejecutar(self, periodo: Periodo, fuente: Fuente, params: dict) -> list[Resultado]: ...

    # solo clase REPORTE
    def consultar(self, periodo: Periodo, filtros: dict) -> dict: ...
```

**Hay dos clases de motor y no tienen la misma forma.** Cinco de los seis concilian: consumen archivos, cruzan contra un soporte y producen hallazgos. El de flujo de caja no concilia nada — lee los movimientos ya categorizados y arma reportes. No implementa `validar` ni `ejecutar`.

En el frontend, `src/registro.ts` mapea cada `slug` a sus rutas y componentes. Agregar un motor es agregar una carpeta y una línea al registro.

### Advertencia importante

**Este contrato es un borrador.** Está escrito para que tengas una forma de trabajo, no porque sepamos que es la correcta. La forma definitiva la revela el **segundo** motor, no el primero.

Construí el núcleo lo más simple que puedas para que `conciliacion_wallets` funcione de punta a punta. Cuando arranque el segundo motor, lo que ambos necesiten sube al núcleo y ahí ajustamos el contrato. **No abstraigas para motores que todavía no existen** — es la forma más común de que un proyecto como este se detenga.

---

## §6 · API DEL NÚCLEO

```
POST   /api/v1/auth/login             JWT en cookie HttpOnly, Secure, SameSite=Strict
POST   /api/v1/auth/logout
GET    /api/v1/auth/me

GET    /api/v1/empresas
GET    /api/v1/fuentes?empresa=&motor=
GET    /api/v1/motores                 los registrados, con su clase

GET    /api/v1/periodos
POST   /api/v1/periodos                                  (admin)
POST   /api/v1/periodos/{id}/cerrar                      (admin)
POST   /api/v1/periodos/{id}/reabrir                     (admin, va a auditoría)

POST   /api/v1/cargas                  multipart; corre la validación del motor
GET    /api/v1/cargas?periodo=&fuente=
DELETE /api/v1/cargas/{id}             solo con período abierto

GET    /api/v1/movimientos?periodo=&fuente=&estado_categoria=&categoria=&q=
PATCH  /api/v1/movimientos/{id}        categorizar; devuelve sugerencia de regla
POST   /api/v1/movimientos/lote        categorizar varios a la vez

GET    /api/v1/reglas?motor=&fuente=
POST   /api/v1/reglas
PATCH  /api/v1/reglas/{id}
POST   /api/v1/reglas/importar         carga masiva desde el catálogo existente
POST   /api/v1/reglas/{id}/reaplicar

POST   /api/v1/cierres/ejecutar        {periodo, motor, fuente}; 409 si hay carga bloqueada
GET    /api/v1/cierres/{periodo}/resumen
GET    /api/v1/resultados?periodo=&motor=&regla=&estado=

GET    /api/v1/hallazgos?periodo=&motor=&estado=&responsable=&severidad=
PATCH  /api/v1/hallazgos/{id}          asignar, justificar, escalar, resolver
POST   /api/v1/hallazgos/lote

GET    /api/v1/parametros?motor=&fuente=
PUT    /api/v1/parametros              crea versión nueva, nunca sobrescribe (admin)

GET    /api/v1/export/{periodo}.xlsx
GET    /api/v1/auditoria?desde=&hasta=&usuario=
GET    /api/health                     {"status":"ok","database":"connected"}
```

Filtros de período: hoy, últimos 7, últimos 30, este mes, mes anterior, este año, rango libre.

**Todos los cálculos van en el backend. El frontend solo presenta.**

---

## §7 · ROLES

| Permiso | admin | analista | contabilidad | auditor |
|---|---|---|---|---|
| Cargar archivos | Sí | Sí | No | No |
| Ejecutar un cierre de motor | Sí | Sí | No | No |
| Categorizar movimientos | Sí | Sí | No | No |
| Crear o editar reglas | Sí | Sí | No | No |
| Justificar o escalar hallazgos | Sí | Sí | Solo comentar | No |
| Editar parámetros | Sí | No | No | No |
| Cerrar o reabrir período | Sí | No | No | No |
| Exportar y ver bitácora | Sí | Sí | Sí | Sí |
| Gestionar usuarios | Sí | No | No | No |

**Los permisos se validan en el backend, como dependencia de FastAPI.** Ocultar un botón en React no es un control de acceso.

---

## §8 · EXPORT A EXCEL

El export tiene que servir para que contabilidad no note el cambio de herramienta.

- **Hoja `MOVIMIENTOS`** — una fila por movimiento con exactamente las columnas de la hoja actual y en el mismo orden: FECHA PAGO OPORTUNO · FECHA · INGRESO/EGRESO · MONTO · DESCRIPCION · CIUDAD · UNID. NEGOCIO · CATEGORIA · EMPRESA · TERCERO · MODALIDAD · FIJO / VARIABLE · RECIBO PAGO/CAJA · Mes Real · AÑO · # Mes Real · CAUSACION · SEMANA. Los cuatro derivados se calculan al exportar.
- **Hoja `RESUMEN`** — score por motor y por fuente, totales, montos en juego.
- **Una hoja por regla de conciliación** con el detalle de sus hallazgos.
- **Hoja `PENDIENTES`** — los movimientos sin categorizar.

---

## §9 · SEGURIDAD

- Passwords con **Argon2**.
- JWT en **cookie HttpOnly, Secure, SameSite=Strict**. Nada de tokens en `localStorage`.
- Secretos solo por variables de entorno. `.env` en `.gitignore`. Nunca secretos en Git.
- Rate limiting en `/auth/login`.
- Validación estricta de archivos subidos: extensión, tipo MIME, tamaño máximo, apertura en modo solo lectura.
- `/docs` de FastAPI desactivable por configuración en producción.
- Manejo centralizado de excepciones, formato consistente, **sin stack traces al cliente**:
  ```json
  { "error": { "code": "CARGA_DUPLICADA", "message": "Este archivo ya se cargó el 14 de septiembre" } }
  ```
- Logging estructurado: `request_id`, `usuario_id`, endpoint, status, duración. **Nunca** passwords, tokens ni secretos.

**Los mensajes de error van en castellano y dicen qué hacer, no un código de excepción.** Los usuarios son contadores y analistas, no desarrolladores.

---

## §10 · INFRAESTRUCTURA

### Nginx
Único servicio expuesto. Sirve el React compilado y hace proxy de `/api/*` al backend. `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Real-IP`, gzip, headers de seguridad, `client_max_body_size 64M` (los Excel pesan), timeouts amplios para los cierres, `try_files $uri $uri/ /index.html`. Sin `server_tokens`.

### Docker Compose (producción)
Levanta `postgres`, `backend`, `nginx`. El frontend se compila y Nginx lo sirve estático. `restart: unless-stopped`, healthchecks (`pg_isready`, `/api/health`), volumen persistente, red privada de Docker.

**El puerto 5432 no se publica al host.** Tampoco 8000 ni 5173.

### Lightsail y DNS
Ubuntu 24.04, **4 GB de RAM** — pandas sobre ~60.000 filas queda al límite con 2 GB. IP estática. Firewall: 80 y 443 abiertos, SSH restringido por IP donde sea posible.

Subdominio de `asiati.com.co` con registro `A` a la IP estática. Cloudflare en modo proxy oculta la IP y agrega WAF básico. Certificado con Certbot, renovación automática.

**El sistema debe funcionar también sobre la IP en HTTP**, sin dominio, para pruebas internas. Documentá las dos rutas.

### Despliegue
```bash
git clone <repo> && cd plataforma-financiera
cp .env.example .env && nano .env
docker compose -f docker-compose.prod.yml up -d --build
docker compose exec backend alembic upgrade head
docker compose ps
curl localhost/api/health
```

Alembic para migraciones. **Nunca `create_all()` en producción.**
`scripts/backup-db.sh` con `pg_dump`, diseñado para subir a S3 después sin reescribirlo. `scripts/restore-db.sh` documentado y probado de verdad, no solo escrito.

### `.env.example`
```
APP_ENV=production
POSTGRES_DB=plataforma
POSTGRES_USER=plataforma_user
POSTGRES_PASSWORD=
DATABASE_URL=
SECRET_KEY=
ACCESS_TOKEN_EXPIRE_MINUTES=480
ALLOWED_ORIGINS=
DOCS_ENABLED=false
VITE_API_URL=/api
```

---

## §11 · DISEÑO VISUAL

Tipografía: **Montserrat** (400–800) para todo. **JetBrains Mono** para IDs, referencias, montos en tabla y etiquetas técnicas.

```css
--navy:      #061428;   /* fondos oscuros, sidebar */
--ink:       #0A1F3C;   /* texto principal */
--blue:      #1B5FB0;   /* acción, activo, acento */
--blue-soft: #6FA8E8;   /* gráficas secundarias */
--mist:      #EFF4FA;   /* fondos suaves, chips */
--border:    #D7E3F2;
--white:     #FBFCFE;   /* fondo de app */
--text-2:    #4E617C;
--gold:      #FFC845;   /* SOLO alertas */
--ok:        #1B7F63;
--crit:      #B5372F;
```

- El oro es **semántico**, no decorativo.
- **El color nunca dice solo.** Cada estado lleva su palabra: `En orden`, `Revisar`, `Pendiente`, `Crítico`, `No aplica`. Tiene que entenderse impreso en blanco y negro.
- Los KPI muestran **pesos primero, conteos después**.

Layout: sidebar navy fija de 216 px · header con empresa, motor y período · KPI cards · gráficas · tablas.

Navegación: **empresa → motor → sección**. Así piensa el usuario, aunque el código no esté organizado así.

---

## §12 · CRITERIOS DE ACEPTACIÓN DEL NÚCLEO

El núcleo está listo cuando, **sin que exista ningún motor**, se puede:

1. Iniciar sesión con cada uno de los cuatro roles y verificar que los permisos se aplican en el backend.
2. Crear un período y cerrarlo; comprobar que un período cerrado rechaza escrituras.
3. Cargar un archivo y ver sus filas en `movimientos` con el `crudo` intacto.
4. Cargar **el mismo archivo otra vez** y recibir un rechazo por hash, sin filas duplicadas.
5. Importar un catálogo de reglas y ver los movimientos quedar en `AUTO`, `REVISAR` o `PENDIENTE`.
6. Resolver un `PENDIENTE` a mano, aceptar la sugerencia de regla, y ver que un movimiento igual del período siguiente llega ya en `AUTO`.
7. Crear un hallazgo de prueba y moverlo por todo su ciclo de vida.
8. Exportar el Excel y comprobar que la hoja `MOVIMIENTOS` tiene las 18 columnas en orden.
9. Ver en `auditoria` cada una de las acciones anteriores, con autor, fecha y el antes y después.
10. Clonar el repo en una Lightsail limpia y desplegar siguiendo solo el README.

### Tests obligatorios

Permisos por rol contra cada endpoint · idempotencia de carga por hash · período cerrado rechaza escrituras · categorizador con match por patrón y sufijo variable · regla con `requiere_revision` que no auto-clasifica · aprendizaje de regla y su aplicación al período siguiente · aritmética con `Decimal` sin pérdida de precisión · el export con las 18 columnas · filtros de período y comparación contra el período anterior.

---

## §13 · FORMA DE TRABAJAR

Antes de modificar archivos: inspeccioná lo que existe, no destruyas funcionalidad, planteá brevemente lo que vas a implementar, y después implementá.

No pidas confirmación para decisiones técnicas menores. Tomá decisiones razonables. Si encontrás algo que comprometa la integridad de los datos, la seguridad o la mantenibilidad, corregilo antes de continuar.

Antes de dar algo por terminado: corré los tests, revisá imports, verificá migraciones, validá el build de Docker y `docker compose config`, y comprobá que no haya secretos en el repositorio. **No declares nada terminado si no lo validaste.**

**Interfaz, mensajes de error y nombres de campo visibles en castellano. Código, variables y commits en inglés.**

### Lo que NO tenés que hacer

- No implementes reglas de negocio de ningún motor.
- No abstraigas para motores que no existen.
- No agregues Redis, colas ni microservicios.
- No inventes campos en `movimientos`: la lista de §3 salió de la hoja real que usa contabilidad.

Si algo del dominio no te queda claro, preguntá antes de asumir. Las reglas de negocio son del otro frente, y adivinarlas cuesta más que preguntarlas.
