# Preflight de aplicación de correcciones de Wallets (fase segura)

Este endpoint es una evaluación exclusivamente de lectura, vinculada al expediente, la empresa y el período. Verifica estado abierto, decisión financiera, segregación, ejecución de reapertura, carga original y existencia de un historial de conciliación asociado. La respuesta indica bloqueos concretos.

**El resultado siempre devuelve `puede_aplicar=false` y `aplicada=false`** hasta disponer de una fuente canónica por movimiento, comparación de importe original contra el expediente y mecanismo de escritura contable transaccional. La referencia textual `movimiento_ref`, los importes declarados y la referencia de evidencia no son por sí mismos comprobación del movimiento. Una conciliación agregada en JSON tampoco acredita el valor individual.

Para habilitar un motor real debe existir como mínimo: identidad estable por movimiento; trazabilidad de fila/archivo y hash de la carga; comparación del importe contra la fuente persistida y vigente; autorización segregada; índice de idempotencia por movimiento y tipo de corrección; prueba de efectos en saldos; registro inmutable de antes/después; rollback atómico ante error y pruebas PostgreSQL con concurrencia. No se habilita cierre de períodos ni ajuste de saldos con este PR.

## Riesgo pendiente
El servicio general `reabrir_periodo` continúa existiendo; hay que auditar todos sus llamadores y garantizar que no pueda eludir el expediente de reapertura aprobado.
