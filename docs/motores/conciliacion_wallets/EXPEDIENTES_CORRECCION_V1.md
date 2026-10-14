# Expedientes de corrección de Wallets — Etapa siguiente

El expediente es **documental y no ejecuta ajustes financieros**. Cada propuesta requiere: reapertura ejecutada en la misma empresa/período, período actualmente abierto, carga original de esa empresa/período, referencia del movimiento original, valor anterior/propuesto con máximo dos decimales, referencias a evidencia antes/después y justificación.

Conciliación prepara el expediente. Coordinación Financiera puede registrar una sola decisión (`AUTORIZAR_EJECUCION` o `RECHAZAR`), con segregación del preparador y auditoría transaccional. La decisión `AUTORIZAR_EJECUCION` **no aplica** ningún cambio al movimiento o saldo. Tampoco vuelve a cerrar el período. `puede_cerrar=false` sigue vigente.

## Riesgos y gates pendientes
- El vínculo a `cargas.id` valida identidad de empresa/período, pero `movimiento_ref` y las evidencias son referencias declaradas **sin comprobación automática contra el contenido del archivo**.
- Antes de permitir una aplicación real, corroborar la fila original y sus montos, crear una bitácora inmutable de ejecución, exigir aprobación financiera formal, evitar doble aplicación, verificar reversibilidad y hacer tests HTTP/PostgreSQL completos.
- Auditoría y estado de período deberán garantizar una transacción única en la operación futura. Ni la carga original ni el archivo base se reescriben en esta versión.
