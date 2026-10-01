# 0007 — Amazon Cognito para autenticación; autorización permanece en PostgreSQL

- Fecha: 2026-10-01
- Estado: Aceptada
- Alcance inicial: desarrollo
- User Pool de desarrollo: `financial-system-asiati-dev`

## Contexto

La plataforma almacenaba hashes Argon2 de contraseña en `usuarios.password_hash` y
resolvía login, cambio de contraseña, bloqueo por intentos y restablecimiento dentro de
FastAPI/PostgreSQL.

El modelo de permisos, en cambio, ya está separado de la contraseña y depende de:

- `usuarios.rol`;
- `usuario_empresas`;
- `app/core/permisos.py`;
- auditoría e ingresos.

Se requiere externalizar la gestión de credenciales sin mover reglas financieras ni
perder el alcance por empresa.

## Decisión

Amazon Cognito User Pools pasa a ser la fuente de verdad de **identidad y contraseña**.

PostgreSQL sigue siendo la fuente de verdad de **autorización de la plataforma**:

- usuario local;
- rol;
- empresas asignadas;
- activo/inactivo;
- permisos efectivos;
- auditoría e ingresos.

No se usan Cognito Groups para replicar roles financieros.

## Flujo

### Login

1. El navegador mantiene el formulario propio de la plataforma.
2. FastAPI recibe correo y contraseña por HTTPS.
3. FastAPI usa `InitiateAuth / USER_PASSWORD_AUTH` contra Cognito.
4. Si Cognito autentica, la API exige que exista un `Usuario` local activo.
5. Se emite la cookie HttpOnly `asiati_sesion` existente.
6. Los endpoints siguen autorizando contra rol y empresas locales.

La contraseña no se persiste en PostgreSQL.

### Primer ingreso

Los usuarios creados administrativamente en Cognito pueden llegar con
`NEW_PASSWORD_REQUIRED`. La API conserva el flujo actual de primer ingreso y responde el
challenge con `RespondToAuthChallenge`.

Los usuarios creados desde la API de la plataforma usan `SignUp` con el app client
confidencial. Cognito envía un código al correo; la pantalla permite confirmar la cuenta.
Después, la marca local `debe_cambiar_password` obliga a reemplazar la contraseña temporal.

### Recuperación

`ForgotPassword` y `ConfirmForgotPassword` de Cognito reemplazan el
restablecimiento local de contraseña. La plataforma conserva una marca aleatoria local para
invalidar sesiones web abiertas.

## Compatibilidad de esquema

Este cambio **no agrega una migración Alembic**.

La columna histórica `usuarios.password_hash` se conserva temporalmente para evitar una
migración concurrente. Cuando `AUTH_PROVIDER=cognito`, no contiene un hash de la contraseña:
contiene una marca aleatoria `external-session:...` cuya única función es invalidar JWT de
sesión anteriores.

En modo `AUTH_PROVIDER=local`, la columna conserva su semántica Argon2 anterior.

## App client

El app client de Cognito es confidencial y tiene client secret.

- El secret nunca se sirve al navegador.
- No se versiona en Git.
- El deploy de desarrollo lo obtiene con OIDC desde
  `DescribeUserPoolClient` y lo escribe únicamente en el archivo de entorno del servidor.
- Todas las llamadas de cliente incluyen el `SECRET_HASH` requerido por Cognito.

Esto evita exponer un app client de registro abierto mientras permite que el backend cree
usuarios mediante las APIs públicas de User Pools sin credenciales IAM persistentes en
Lightsail.

## Controles conservados

La plataforma conserva además de Cognito:

- límite local de intentos fallidos;
- registro de intentos en `ingresos`;
- `ultimo_ingreso_at`;
- usuario local activo/inactivo;
- cookie Secure + HttpOnly + SameSite=Strict;
- auditoría de cambio y restablecimiento.

## MFA

MFA queda desactivado en esta primera migración porque la UI actual no implementa los
challenges TOTP/SMS. Activarlo requiere un PR posterior que cubra enrollment, challenge y
recuperación. No se habilitará SMS por defecto.

## Rollback

`AUTH_PROVIDER=local` reactiva el flujo anterior sin cambios de esquema. El User Pool no se
elimina durante un rollback.
