# Catálogo de cobertura Wallets V1 — PR3

Esta primera etapa agrega la tabla `wallets_esperadas` por empresa/período/tipo/identidad, sin inferir cobertura a partir de cargas existentes.

**No hay siembra automática ni registro editable en este PR.** Los registros requieren un proceso autorizado futuro, con validación frente a catálogos de wallets de la empresa, vigencia y auditoría de altas/bajas. Una tabla vacía se interpreta como cobertura **no definida**, nunca como lista vacía aprobada.

Identidad: `wiilog` utiliza cadena vacía por ser la wallet principal configurada en runtime; `tienda` y `pagos` usan identidad normalizada en minúsculas. No se versionan correos reales.

El diagnóstico compara cada clave esperada con la última ejecución persistida de esa wallet. Una wallet faltante bloquea siempre aunque exista una excepción documentada. C0 inválido y cualquier hallazgo pendiente también bloquean.

**Importante:** este catálogo aún no tiene firma/aprobación formal; `puede_cerrar=false` no cambia. Para habilitar cierres faltan responsables, aprobación, corte horario, evidencia, rutas autorizadas y protección transaccional.

## Integridad y reglas de diagnóstico

La migración 0025 crea una clave única auxiliar en `periodos(id, empresa_id)` y una clave foránea compuesta desde `wallets_esperadas(periodo_id, empresa_id)`. PostgreSQL impide asociar una wallet esperada a un período de otra empresa.

Se distinguen tres categorías: wallets esperadas con conciliación (cobertura), wallets esperadas faltantes (bloqueo) y ejecuciones adicionales no declaradas (reportadas separadamente, sin convertirlas en obligatorias). La política final para las adicionales requiere definición financiera; este preflight no autoriza cierres.

No debe cargarse el catálogo mediante SQL manual como procedimiento operativo. Queda por implementar un flujo de alta/baja y aprobación financiera con auditoría, vigencia, identificación segura de wallets y congelación tras cierre.
