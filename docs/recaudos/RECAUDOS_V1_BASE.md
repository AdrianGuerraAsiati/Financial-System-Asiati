# Recaudos V1 · Base de registro y bandeja (sin conciliación)

**Objetivo:** registrar de forma trazable ingresos que un operador informa, mantenerlos por empresa y preparar la integración futura con bancos y Cartera. La información inicial procede de las conversaciones de fase 4 y del modelo existente de permisos, no de una fuente bancaria aprobada.

## Alcance incluido

- Pantalla independiente **Recaudos → Ingresos reportados** con registro manual, búsqueda por referencia/cuenta/pagador, filtros por moneda y fechas, paginación, detalle y anotación de estado.
- API bajo `/api/v1/recaudos/ingresos` para crear, listar y consultar por ID.
- Captura: empresa (obtenida del selector de sesión y comprobada por backend), fecha reportada, monto, moneda, cuenta receptora, referencia externa, pagador informado y descripción opcional.
- Origen del registro **MANUAL** y estado inmutable **PENDIENTE_VERIFICACION** en esta V1.
- Unicidad empresa + cuenta receptora normalizada + referencia externa normalizada. Repeticiones se rechazan con 409, incluso si la fecha reportada es distinta. El usuario debe revisar el caso; no se fusionan movimientos.
- Auditoría del alta en la misma transacción que la captura.
- `NUMERIC(18,2)`, montos positivos y finitos, prohibición de más de dos decimales, y consulta paginada (máximo 100 por respuesta).
- Restricción backend por empresa y permisos. Sin datos ni referencias bancarias almacenadas en archivos versionados.

## Qué NO hace

El registro no demuestra que exista una transferencia ni un abono bancario real. No cuenta como dinero recaudado, no crea comprobante de banco, no concilia extractos o Wallets, no genera asientos contables, no marca facturas pagadas ni modifica saldos, vencimientos o estados de Cartera. Se evita expresamente cualquier endpoint para declarar un abono «confirmado» mientras falte definir la fuente de verdad y las reglas de conciliación.

No se importan CSV/Excel, no se hace OCR, no se consultan bancos ni Google Sheets y no se realiza escritura inversa. La columna «cuenta receptora» se mantiene como identificador manual; aún no hay un catálogo bancario aprobado.

**Nota de alcance:** los comprobantes de cobro de Cartera y los de pago de proveedores en Tesorería no constituyen confirmación bancaria de un recaudo reportado.

## Permisos

- `recaudos.ver`: superadministrador (todas), coordinación financiera (asignadas), analista de tesorería (asignadas), TI (lectura de todas).
- `recaudos.registrar`: superadministrador (todas) y analista de tesorería (asignadas).
- Rol conciliación y demás roles no indicados: sin acceso hasta que negocio apruebe el flujo.
- Intentar acceder a empresa ajena devuelve 404 tanto en bandeja como en detalle y alta.

## Datos y futuras integraciones

- Tabla `recaudos_ingresos_reportados`, migración `0023_recaudos_reportados` con claves únicas e índices empresa+fecha.
- Cada fila tiene referencia de origen, fecha y monto **reportados** y una referencia auditada al usuario que capturó.
- Futuros motores podrán incorporar un identificador externo inmutable, lote, hash del archivo fuente y evidencia real, una vez definido el formato de cada banco. La verificación y aplicación requerirán un contrato separado y trazabilidad evento a evento.
- No se conectan claves foráneas a compras ni a Cartera sin validar el identificador de obligación (véase issue #137).

## Pruebas técnicas

`pytest -q tests/test_core_recaudos_api.py tests/test_permisos_matriz.py`

Cubren permisos por rol/empresa, duplicados con normalización, validación de montos y estados, paginación, auditoría y garantía de que no hay acciones de confirmación. El PR debe superar CI, seguridad y migración.

## Comprobaciones funcionales aplazadas por el usuario

Aplazadas, no aprobadas: validar con extractos y referencias bancarias reales, comparar la nueva bandeja con los registros de Recaudos, definir cómo asociar los movimientos a facturas/clientes/OC y aprobar la fuente de verdad. **No registrar movimientos ficticios con datos reales.** El despliegue en desarrollo no implica aprobación financiera ni operación en producción.
