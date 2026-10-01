# Roles y permisos · Plataforma Financiera ASIATI

Versión 1 · 28 de septiembre de 2026 · Define: Juan Felipe Parra (Coordinación de Datos Estratégicos)

Este documento reemplaza la tabla de roles de `SPEC_NUCLEO.md §7` (admin, analista, contabilidad, auditor).

---

## 1. Los roles

Hay tres roles activos desde el primer entregable y dos que se crean ya en el modelo pero se activan después.

| Código | Nombre visible | Quién | Para qué |
|---|---|---|---|
| `super_administrador` | Superadministrador | Juan Felipe | Crea usuarios, asigna roles y empresas, habilita procesos. Puede hacer todo lo que hacen el conciliador y el coordinador. |
| `coordinacion_financiera` | Coordinador financiero | Supervisor del equipo | Ve el estado de las conciliaciones, los últimos ingresos y las acciones de cada conciliador. Resuelve los casos especiales que le escalan. |
| `conciliacion` | Conciliador financiero | Operativo | Carga archivos, ejecuta conciliaciones, categoriza movimientos y gestiona hallazgos de las empresas que tiene asignadas. |
| `analista_tesoreria` | Analista de tesorería | Futuro | Se activa con el bloque de bancos y tesorería. Hoy existe en el modelo, sin permisos. |
| `ti` | Soporte técnico | Adrian | Arregla problemas de la plataforma: errores, cargas fallidas, infraestructura. No toma decisiones financieras. |

**Los roles son fijos en el código.** El superadmin asigna roles a usuarios; no crea roles nuevos desde la pantalla. Un rol nuevo (como analista de tesorería) se agrega por código, con su fila en la matriz de la sección 3. Crear roles desde la interfaz es un proyecto en sí mismo y no lo necesitamos para operar.

Un usuario tiene un solo rol.

Los códigos de rol siguen la convención de la migración `0009_create_usuarios_roles` (minúsculas, snake_case). Las cinco filas de la columna "Código" son exactamente los valores del CHECK de `usuarios.rol`.

---

## 2. Empresas asignadas

- Las empresas son `WIILOG`, `CHIN CHIN` y `ASIATI COMERCIAL` al arranque. Se agregan más como filas, nunca como código.
- El superadmin asigna a cada usuario una o varias empresas (`usuario_empresas`).
- **Conciliador financiero:** solo ve y opera las empresas asignadas. En el selector de empresa solo aparecen esas.
- **Coordinador financiero:** ve las empresas que tenga asignadas. Por defecto, al crearlo, se le asignan todas.
- **Superadmin y TI:** ven todas.
- La restricción se aplica **en el backend** en cada consulta y cada acción. Ocultar la empresa en el menú no es un control de acceso.
- Intentar abrir algo de una empresa no asignada responde 404, no 403: no se confirma que exista.

---

## 3. Matriz de permisos

`Sí` = puede · `Asig.` = solo en sus empresas asignadas · `Leer` = solo consulta · `—` = no puede

| Permiso (código) | Qué permite | Superadmin | Coordinador | Conciliador | TI | Analista tesorería |
|---|---|---|---|---|---|---|
| `usuarios.gestionar` | Crear, editar, desactivar usuarios; asignar rol y empresas | Sí | — | — | — | — |
| `empresas.gestionar` | Crear empresas y habilitar procesos por empresa | Sí | — | — | — | — |
| `parametros.editar` | Crear una versión nueva de parámetros de un motor | Sí | — | — | — | — |
| `parametros.ver` | Ver parámetros y su historial de versiones | Sí | Sí | Asig. | Leer | — |
| `cargas.subir` | Subir archivos (wallet, órdenes, extractos) | Sí | — | Asig. | — | — |
| `cargas.eliminar` | Borrar una carga de un período abierto | Sí | — | Asig. | — | — |
| `conciliacion.ejecutar` | Correr la conciliación de un período y fuente | Sí | — | Asig. | — | — |
| `conciliacion.ver` | Ver resultados, hallazgos y resumen | Sí | Asig. | Asig. | Leer | — |
| `cartera.ver` | Ver operaciones, mora, proyección y comprobantes | Sí | Asig. | Asig. | Leer | — |
| `compras.ver` | Ver líneas, estados y catálogos de Compras/Supply Chain | Sí | Asig. | Asig. | Leer | — |
| `cartera.comprobantes.subir` | Radicar comprobantes de pago | Sí | — | Asig. | — | — |
| `movimientos.categorizar` | Cambiar categoría y escribir observación | Sí | Asig. | Asig. | — | — |
| `reglas.crear` | Guardar una regla de categorización nueva | Sí | Asig. | Asig. | — | — |
| `hallazgos.gestionar` | Asignar, justificar, marcar resuelto | Sí | Asig. | Asig. | — | — |
| `hallazgos.escalar` | Enviar un caso especial al coordinador con una pregunta | Sí | — | Asig. | — | — |
| `hallazgos.responder_escalado` | Responder o decidir un caso escalado | Sí | Asig. | — | — | — |
| `periodos.cerrar` | Cerrar un período | Sí | Asig. | — | — | — |
| `periodos.reabrir` | Reabrir un período cerrado, con motivo | Sí | — | — | — | — |
| `supervision.ver` | Tablero de supervisión: estado de conciliaciones, últimos ingresos, acciones por usuario | Sí | Asig. | — | — | — |
| `auditoria.ver` | Bitácora completa con antes y después | Sí | Asig. | — | Leer | — |
| `exportar` | Descargar Excel de resultados y movimientos | Sí | Asig. | Asig. | — | — |
| `sistema.ver` | Salud del sistema, errores, cargas fallidas, trabajos en cola | Sí | — | — | Sí | — |
| `sistema.reprocesar` | Reintentar una carga o un trabajo fallido, sin cambiar datos | Sí | — | — | Sí | — |

Notas:
- **Cerrar período** lo hace el coordinador (supervisa) y el superadmin; el conciliador no cierra su propio trabajo.
- **TI no modifica datos financieros.** Puede ver resultados para diagnosticar un error y reprocesar lo que falló, siempre dejando rastro en auditoría. Si un arreglo exige cambiar un dato, lo hace un superadmin.
- **Analista de tesorería** queda sin permisos hasta el bloque de tesorería.
- **Cartera:** el mapeo inicial replica el alcance de consulta de conciliación y el patrón operativo de carga. Puede ajustarse cuando negocio defina un rol específico de cartera.
- **Compras:** `compras.ver` es estrictamente de lectura. El alcance inicial replica otros permisos de consulta y puede ajustarse cuando negocio defina perfiles específicos de Supply Chain.

---

## 4. El flujo de caso especial

Un hallazgo que el conciliador no puede decidir solo pasa al coordinador:

```
detectado → en_gestion → escalado → en_gestion → resuelto → cerrado
                              ↑           │
                              └─ pregunta ─┘  (el coordinador responde o decide)
```

- `escalar` exige una pregunta escrita. Queda el autor, la fecha y la pregunta.
- `observar` (permiso `hallazgos.gestionar`) deja una observación escrita (mensaje `NOTA`) y pasa el hallazgo a `en_gestion`, o a `resuelto` si se marca resolver. No aplica a hallazgos escalados: esos los decide el coordinador.
- El coordinador ve una bandeja "Casos escalados" con los de sus empresas.
- La respuesta del coordinador queda en el hilo del hallazgo y el caso vuelve al conciliador, o el coordinador lo resuelve directamente.
- Todo el hilo queda en auditoría.

---

## 5. Lo que ve el coordinador (tablero de supervisión)

1. **Estado de conciliaciones** por empresa, fuente y período: pendiente, ejecutada, cerrada; score; hallazgos abiertos en pesos y cantidad.
2. **Últimos ingresos**: usuario, rol, fecha y hora, IP. Últimos 30 días.
3. **Acciones por conciliador**: cargas, ejecuciones, categorizaciones, hallazgos gestionados; filtros por usuario, empresa y fechas.
4. **Casos escalados** esperando su respuesta.

Todo sale de la tabla `auditoria` y de una tabla de ingresos. No se construyen contadores aparte.

---

## 6. Modelo de datos

```sql
-- rol como texto con CHECK, no tabla de roles
usuarios
  id, email UNIQUE, nombre, password_hash,       -- Argon2
  rol TEXT NOT NULL CHECK (rol IN ('super_administrador','coordinacion_financiera','conciliacion','analista_tesoreria','ti')),
  activo BOOL NOT NULL DEFAULT true,
  debe_cambiar_password BOOL NOT NULL DEFAULT true,
  ultimo_ingreso_at TIMESTAMPTZ NULL,
  creado_por BIGINT NULL, creado_at TIMESTAMPTZ NOT NULL DEFAULT now()

usuario_empresas
  usuario_id, empresa_id, asignado_por, asignado_at
  PRIMARY KEY (usuario_id, empresa_id)

ingresos                                         -- cada login, exitoso o fallido
  id, usuario_id NULL, email_intentado, exito BOOL, ip, user_agent, creado_at

auditoria                                        -- ya en SPEC_NUCLEO §3
  id, usuario_id, empresa_id NULL, accion, entidad, entidad_id, antes JSONB, despues JSONB, ip, creado_at

hallazgo_mensajes                                -- el hilo del caso especial
  id, hallazgo_id, usuario_id, tipo TEXT CHECK (tipo IN ('PREGUNTA','RESPUESTA','NOTA')), texto, creado_at
```

> **Autenticación:** en entornos con `AUTH_PROVIDER=cognito`, Cognito autentica
> correo/contraseña y PostgreSQL conserva exclusivamente la autorización descrita en
> este documento. Roles y empresas no se duplican en Cognito Groups. La columna
> histórica `password_hash` funciona como marca de invalidación de sesión y no como
> almacenamiento de la contraseña externa. Ver ADR 0007.

Los permisos viven en código:

```python
# app/core/permisos.py
PERMISOS: dict[str, dict[str, Alcance]] = {
    "cargas.subir": {ROL_SUPER_ADMINISTRADOR: Alcance.TODAS, ROL_CONCILIACION: Alcance.ASIGNADAS},
    ...
}
```

---

## 7. Reglas de implementación

**Backend**
- Una dependencia de FastAPI por endpoint: `Depends(requiere("cargas.subir", empresa_de=...))`. Revisa el permiso y, si el alcance es `ASIGNADAS`, que la empresa del recurso esté en `usuario_empresas`.
- Las consultas de listas filtran por empresas asignadas en el repositorio, no en el endpoint, para que ningún listado nuevo las olvide.
- Toda acción que cambia datos escribe en `auditoria` en la misma transacción.
- Cada login escribe en `ingresos` y actualiza `ultimo_ingreso_at`.
- Sesión: JWT en cookie HttpOnly, Secure, SameSite=Strict. Límite de intentos en `/auth/login`.
- Al primer ingreso, cambio de contraseña obligatorio.

**Frontend**
- `/auth/me` devuelve usuario, rol, lista de permisos efectivos y empresas asignadas. El frontend solo **presenta**: menú, rutas y botones según esa lista.
- Rutas protegidas por permiso; si falta, pantalla "No tienes acceso a esta sección" con el nombre del superadmin para pedirlo.
- Navegación: empresa → proceso → sección.

**Pruebas obligatorias**
- Cada endpoint contra cada rol: permitido y negado.
- Conciliador con WIILOG asignado no ve ni opera CHIN CHIN (listado vacío y 404 en detalle).
- TI no puede categorizar, justificar ni editar parámetros.
- Escalar sin pregunta es rechazado.
- Cada acción deja su fila en `auditoria`; cada login en `ingresos`.

---

## 8. Endpoints

```
POST   /api/v1/auth/login | /auth/logout | GET /auth/me | POST /auth/cambiar-password
GET    /api/v1/usuarios                       usuarios.gestionar
POST   /api/v1/usuarios                       usuarios.gestionar
PATCH  /api/v1/usuarios/{id}                  usuarios.gestionar   (rol, activo, nombre)
PUT    /api/v1/usuarios/{id}/empresas         usuarios.gestionar
POST   /api/v1/usuarios/{id}/restablecer      usuarios.gestionar
GET    /api/v1/supervision/conciliaciones     supervision.ver
GET    /api/v1/supervision/ingresos           supervision.ver
GET    /api/v1/supervision/acciones           supervision.ver
POST   /api/v1/hallazgos/{id}/escalar         hallazgos.escalar     {pregunta}
POST   /api/v1/hallazgos/{id}/observar        hallazgos.gestionar   {observacion, resolver: bool}
POST   /api/v1/hallazgos/{id}/responder       hallazgos.responder_escalado {respuesta, resolver: bool}
GET    /api/v1/hallazgos?estado=escalado      conciliacion.ver
GET    /api/v1/sistema/salud | /sistema/errores | POST /sistema/cargas/{id}/reprocesar   sistema.*
```
