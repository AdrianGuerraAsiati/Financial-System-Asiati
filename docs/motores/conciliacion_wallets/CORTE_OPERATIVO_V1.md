# Etapa 2 — Corte operativo de Wallets

**Estado:** contrato técnico propuesto; no sustituye aprobación financiera formal. No cierra ni reabre períodos.

## Parámetros obligatorios

Por empresa y período: zona horaria IANA explícita, fecha/hora local del corte, justificación y actor. La fecha del corte debe estar dentro del período. **Decisión operativa del proyecto (cuestionario, sin firma financiera formal): la única zona aceptada es `America/Bogota` (UTC−05:00); otras zonas se rechazan. La hora y fecha exactas del corte siguen sin aprobarse y deben suministrarse expresamente.** Se guarda también el instante UTC calculado y se rechazan horas ambiguas o inexistentes por transiciones DST.

En esta primera versión el registro es único y no modificable desde la API. Cualquier rectificación exige diseñar un proceso de autorización con historial; **no usar SQL manual como corrección operacional**.

## Movimientos posteriores

Clasificación técnica con marcas temporales verificables (no inferidas):
- `EN_CORTE`: instante del movimiento y recepción hasta el corte inclusive.
- `TARDIO_DEL_PERIODO`: movimiento ocurrido hasta el corte, recibido después.
- `POST_CORTE`: movimiento ocurrido después del corte.

La clasificación **no cambia saldos, no reasigna períodos ni ejecuta asientos**. Si el período está cerrado y el movimiento tardío lo afecta, aplicar la decisión anterior: reapertura autorizada con correcciones auditadas, jamás inserción silenciosa.

## Gate financiero pendiente

Finanzas debe ratificar formalmente la zona horaria acordada y autorizar el reloj de corte por empresa/período, semántica de fechas de origen y recepción, tolerancias o márgenes (sin inventarlos), fuente de marcas temporales y procedimiento de correcciones. Hasta entonces, el preflight sigue con `puede_cerrar=false`.
