# Hallazgos de motor con clave estable

Decisión de negocio: `docs/decisiones/0008-categorizacion-manual-wallets.md` (Juan Felipe Parra, 6-oct-2026).
Volver a conciliar con un archivo nuevo **no puede perder** el trabajo del conciliador.

## Qué agrega el núcleo

- `hallazgos.clave` (texto, opcional) con índice único parcial `(periodo_id, motor_slug, clave)` cuando la clave
  existe. La empresa queda fijada por el período. Los hallazgos sin clave siguen funcionando como antes.
- `hallazgos.resuelto_por_sistema` (booleano): distingue lo que resolvió la sincronización de lo que resolvió una
  persona.
- Tipo de mensaje `SISTEMA` en `hallazgo_mensajes`: nota automática firmada por quien ejecutó la conciliación.
- `sincronizar_hallazgos_motor()` en `app/core/hallazgos/sincronizacion.py`.
- `GET /api/v1/hallazgos` y el detalle devuelven `clave` y `resuelto_por_sistema`.

Migración: `0017_hallazgos_clave_estable` (sube y baja limpia; al bajar se borran las notas `SISTEMA`).

## Reglas

El motor entrega todos los hallazgos de un alcance (por ejemplo, una wallet en un período) con su clave
(wallet + regla + `mov_id` u `orden_id`):

| Situación | Resultado |
|---|---|
| La clave no existe | Se crea el hallazgo. |
| La clave existe | Se actualiza la evidencia, la descripción y si es crítico. Se conservan estado, mensajes, escalamiento y `evidencia.categorizacion`. |
| Resuelto **por el sistema** y reaparece | Vuelve a DETECTADO con nota automática. |
| Resuelto **por una persona** y sigue apareciendo | Se queda RESUELTO; solo se actualiza la evidencia. |
| Abierto (detectado, en gestión o escalado) y ya no aparece | RESUELTO por el sistema, con nota automática. |
| Cerrado | No cambia de estado. |

Cada reapertura o resolución automática queda en auditoría (`hallazgo.reabrir_sistema`, `hallazgo.resolver_sistema`).
Un período cerrado no se sincroniza.

## Qué no toca

- No borra hallazgos ni mensajes.
- No cambia la política de cierre: `resuelto` sigue siendo la columna que mira.
- No cambia los endpoints de escalar, observar ni responder.
- No crea la tabla de movimientos.
