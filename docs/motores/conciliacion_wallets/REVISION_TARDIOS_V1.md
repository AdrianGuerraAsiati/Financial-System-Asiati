# Etapa 3 — Revisión de incidencias tardías

Una incidencia temporal detectada en etapa 2 puede recibir **una revisión técnica** por Conciliación (`conciliacion.ejecutar`) con conclusión `REQUIERE_CORRECCION` o `SIN_IMPACTO`, explicación y evidencia referenciada.

Luego **Coordinación Financiera** (`periodos.cerrar`) puede registrar `AUTORIZAR_GESTION` o `RECHAZAR_GESTION`, con justificación. No puede aprobar quien hizo la revisión. Una incidencia solo admite una revisión y una decisión; no se sobreescriben las decisiones.

Los dos pasos se auditan en la misma transacción. `AUTORIZAR_GESTION` significa únicamente **autorizar iniciar un trámite posterior**, no aprobar contablemente el movimiento, ni autorizar reapertura, ni efectuar cierre, ni resolver la incidencia. Para períodos cerrados se exige el flujo de reapertura de Superadministrador por separado, con motivo y auditoría; nunca se modifica el saldo o el período desde estos endpoints.

## Límites pendientes
El campo de evidencia es una referencia declarada, no una prueba de verificación criptográfica. Quedan pendientes vínculo a cargas y movimientos, prueba integrada PostgreSQL de los endpoints, proceso de reapertura y validación formal de Finanzas/Seguridad. `puede_cerrar=false` se mantiene.
