# Administración de wallets esperadas — etapa 1

**Alcance:** catálogo de cobertura por empresa y período, sin cerrar períodos financieros.

## Flujo técnico

- Conciliación (permiso `conciliacion.ejecutar`) prepara el listado: alta y baja con auditoría. Una baja requiere motivo.
- Coordinación Financiera (permiso `periodos.cerrar`) aprueba con justificación, siempre que el catálogo no esté vacío.
- El actor que registró cualquiera de las wallets vigentes no puede aprobarlas él mismo.
- Una vez aprobado, el catálogo queda congelado: no existe endpoint de modificación ni desaprobación.
- El diagnóstico de cierre informa si el catálogo está aprobado, pero **`puede_cerrar=false` sigue fijo**.

## API

- `GET /api/v1/wallets/periodos/{periodo_id}/wallets-esperadas?empresa_id=X`
- `POST /api/v1/wallets/periodos/{periodo_id}/wallets-esperadas?empresa_id=X`
- `DELETE /api/v1/wallets/periodos/{periodo_id}/wallets-esperadas/{item_id}?empresa_id=X` (JSON con motivo)
- `POST /api/v1/wallets/periodos/{periodo_id}/wallets-esperadas/aprobar?empresa_id=X` (JSON con motivo)

El catálogo de Tiendas y Pagos requiere comprobación funcional por Finanzas; el alta valida la pertenencia a los parámetros de la empresa; la vigencia temporal exacta de una wallet aún no está modelada. No se permite declarar el catálogo completo para cierre con esta sola aprobación.

## Pendiente antes de usar en cierres reales

Validar vigencia por fecha y cambios posteriores de los parámetros, pruebas de PostgreSQL y permisos con usuarios reales, manejo excepcional controlado de una aprobación errónea, firma/aceptación financiera, corte temporal y congelación integral del período. No introducir datos sensibles en Git.
