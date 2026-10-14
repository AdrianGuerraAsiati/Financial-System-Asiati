# Solicitud de reapertura por incidencia tardía — propuesta V1

Flujo: Conciliación registra incidencia y revisión; Coordinación Financiera decide AUTORIZAR_GESTION; únicamente el mismo autorizador financiero puede solicitar una reapertura de un período **cerrado** con motivo y evidencia. Superadministración, con permiso `periodos.reabrir`, puede aprobar o rechazar la solicitud una sola vez, dejando auditoría transaccional.

**Límite de seguridad:** aprobar la solicitud NO ejecuta la reapertura, NO modifica `periodos.cerrado`, NO corrige un saldo y NO cierra un período. La ejecución futura debe incorporar comprobación de aprobación vinculada, segregación, bloqueo transaccional, plan de corrección y auditoría; se necesita revisión formal de Finanzas y Seguridad. El servicio antiguo de reapertura deberá revisarse para que no pueda saltarse el flujo aprobado. Hasta entonces `puede_cerrar=false` y no se habilita ninguna ruta nueva de reapertura efectiva.

La corrección posterior queda expresamente fuera de alcance de este PR y requiere su propio modelo transaccional de evidencias, antes/después y referencia a carga/ejecución.
