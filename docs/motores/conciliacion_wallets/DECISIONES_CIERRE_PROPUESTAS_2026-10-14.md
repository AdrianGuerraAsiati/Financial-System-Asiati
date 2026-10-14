# PR3 · Decisiones propuestas para cierre de Wallets (14-oct-2026)

**Estado: insumo de cuestionario, NO aprobación financiera formal.** No habilita cierres.

## Respuestas registradas
1. Exigir todas las wallets esperadas conciliadas, C0 aprobado y sin críticos abiertos.
2. Wallet faltante bloquea, salvo excepción autorizada.
3. C0 descuadrado siempre bloquea; sin tolerancias inventadas.
4. **Todos los hallazgos deben quedar resueltos** (más estricto que solo críticos).
5. Cualquier conciliador puede cerrar (propuesta que contradice la matriz actual).
6. Excepciones solo para casos autorizados por Finanzas, con motivo, responsable y evidencia.
7. Guardar fecha, responsable, empresa, período, ejecuciones, C0, hallazgos, aprobaciones y auditoría.
8. Cualquier conciliador puede reabrir (propuesta que contradice la matriz actual).
9. Congelar conciliaciones y modificaciones financieras hasta reapertura autorizada.
10. Corte operativo con zona horaria, fecha/hora y tratamiento tardío aprobado por Finanzas.

## Compatibilidad y bloqueos
- La condición 4 es más estricta que 1: un informativo o REVISAR pendiente también impide el cierre.
- La regla 2 admite una excepción por wallet faltante, pero 1 exige todas las wallets. Definir si una excepción sustituye una wallet esperada a efectos de cobertura; **nunca** convierte un C0 inválido en aprobado.
- La regla 6 reserva excepciones a Finanzas. Las reglas 5 y 8 piden ampliar permisos de cierre y reapertura a cualquier conciliador, cuando hoy `periodos.cerrar` solo habilita Coordinación Financiera/Superadmin y `periodos.reabrir` solo Superadmin. **No cambiar los permisos sin firma de negocio y seguridad.**
- `app/core/periodos/service.py` ya implementa cierre y reapertura con evento. Su guarda actual impide críticos abiertos, no todos los hallazgos. **No publicar operaciones nuevas sobre ese servicio** sin incorporar las condiciones definitivas y control transaccional.
- No existe definición aprobada de wallets esperadas por empresa/período (vigencia, altas/bajas), casos de excepción, firmantes, corte temporal, zona horaria y manejo de movimientos tardíos.
- La categoría de estado de hallazgos incluye resueltos por sistema; precisar si éstos satisfacen la regla 4 y cómo se congela su evidencia histórica.
- Las evidencias del PR2 registran C0 y resumen, pero deben verificarse cobertura, hash de cargas, versiones de reglas, sello de aprobación y congelación efectiva antes de habilitar cierre.
- El código en PR3 sigue mostrando `puede_cerrar=false` por diseño hasta aprobación formal y desarrollo completo.

## Próxima aprobación requerida
Documento firmado por responsable financiero y responsable de seguridad con alcance de permisos, reglas de cobertura, excepciones, corte, auditoría y reapertura. Registrar la decisión sin datos privados, usando evidencia operacional fuera de Git.
