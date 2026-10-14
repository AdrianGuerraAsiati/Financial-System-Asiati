# Ejecución controlada de reapertura — propuesta V1

La ejecución de reapertura se efectúa mediante la API exclusiva de Superadministración, después de que una solicitud haya sido aprobada. El ejecutor debe ser exactamente quien aprobó esa solicitud, y no puede ser el solicitante. La solicitud y el período se bloquean en la misma transacción, y la ejecución se registra una única vez.

Se exige motivo, referencia del plan correctivo y referencia de evidencia antes del cambio. La misma transacción registra el evento histórico de reapertura, la auditoría y el cambio de `periodos.cerrado` a falso. La operación devuelve `correccion_ejecutada=false`.

**Limitaciones pendientes:** una referencia declarada no verifica contenido ni firma del plan. La función genérica del núcleo `reabrir_periodo` existe y necesita control de todos sus llamadores antes de afirmar que este es el único camino permitido. Queda pendiente implementación de correcciones con evidencia antes/después y mecanismo para volver a cerrar mediante gates completos. `puede_cerrar=false` no cambia. Requiere aprobación formal de Finanzas y Seguridad antes de uso en producción.
