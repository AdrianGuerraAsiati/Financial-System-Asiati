# Catálogo de cobertura Wallets V1 — PR3

Esta primera etapa agrega la tabla `wallets_esperadas` por empresa/período/tipo/identidad, sin inferir cobertura a partir de cargas existentes.

**No hay siembra automática ni registro editable en este PR.** Los registros requieren un proceso autorizado futuro, con validación frente a catálogos de wallets de la empresa, vigencia y auditoría de altas/bajas. Una tabla vacía se interpreta como cobertura **no definida**, nunca como lista vacía aprobada.

Identidad: `wiilog` utiliza cadena vacía por ser la wallet principal configurada en runtime; `tienda` y `pagos` usan identidad normalizada en minúsculas. No se versionan correos reales.

El diagnóstico compara cada clave esperada con la última ejecución persistida de esa wallet. Una wallet faltante bloquea siempre aunque exista una excepción documentada. C0 inválido y cualquier hallazgo pendiente también bloquean.

**Importante:** este catálogo aún no tiene firma/aprobación formal; `puede_cerrar=false` no cambia. Para habilitar cierres faltan responsables, aprobación, corte horario, evidencia, rutas autorizadas y protección transaccional.
