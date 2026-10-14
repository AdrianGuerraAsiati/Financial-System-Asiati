# Registro de movimientos tardíos — etapa 2

Registra observaciones temporales de Wallets por empresa y período, con identificador externo, marcas de ocurrencia y recepción con zona horaria, clasificación y referencia de evidencia. Requiere un corte operativo registrado. La clasificación utiliza el corte de las 23:59:59 del último día calendario en America/Bogota.

Se admiten únicamente `TARDIO_DEL_PERIODO` y `POST_CORTE`; eventos `EN_CORTE` no se guardan como incidencias. El identificador por wallet y período es único. Conciliación puede registrar, y los usuarios con permiso `conciliacion.ver` consultar.

**Importante:** es una bandeja de detección, no una corrección. Las marcas de tiempo provienen de la declaración y aún requieren verificación contra fuente. No se registran asientos, saldos, autorizaciones de reapertura ni cambios del período; en períodos cerrados solo se admite documentar la incidencia. Una corrección posterior exige reapertura autorizada y su propia auditoría. No existe acción para resolver o descartar incidencias en esta etapa.

Faltan validación de evidencias, enlace con ejecución/carga original, revisión de permisos y flujo de tratamiento financiero antes de convertir incidencias en decisiones de cierre.
