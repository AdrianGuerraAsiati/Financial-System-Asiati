# PR3 · Propuesta de reglas de cierre de Wallets (14-oct-2026)

**Estado: decisiones de cuestionario, pendientes de aprobación formal por Finanzas y seguridad.** Este documento no concede permisos ni habilita cierres.

## Condiciones propuestas de cierre

1. Todas las wallets **esperadas para la empresa y período** deben tener última ejecución válida y C0 aprobado. No se inventan tolerancias.
2. Una wallet esperada faltante **bloquea incondicionalmente el cierre**. Puede registrarse una excepción/documento de incidencia, pero **esa excepción NO permite cerrar** ni satisface el requisito de cobertura.
3. Un C0 descuadrado bloquea siempre; una excepción administrativa no transforma C0 inválido en válido.
4. **Todo hallazgo pendiente**, crítico o no, bloquea. Hallazgos **resueltos por el sistema** se consideran resueltos cuando conservan evidencia y trazabilidad verificable. No equivale a eliminar el hallazgo ni a omitirlo del historial.
5. Los conciliadores **solicitan** el cierre. **Coordinación Financiera ejecuta/autoriza** el cierre. **Superadministración reabre**, con motivo obligatorio y auditoría. Esto coincide en lo esencial con la matriz actual de permisos; la solicitud es un flujo **nuevo, todavía no implementado**.
6. Excepciones de carácter administrativo o incidencias: casos permitidos por Finanzas, con motivo, responsable y evidencia. No anulan las condiciones 1 a 4. El catálogo de excepciones admitidas sigue pendiente.
7. Al cerrar, preservar fecha, responsable, empresa, período, ejecuciones y sus C0, estados/evidencia de hallazgos, aprobaciones, hashes/referencias de cargas, versiones aplicables y eventos auditados.
8. Bloquear nuevas conciliaciones y modificaciones financieras del período cerrado. Una operación tardía que afecte dicho período exige **reapertura autorizada por Superadmin**, con motivo y traza de correcciones; **no** se incorpora silenciosamente.
9. El corte requiere una definición explícita de Finanzas sobre zona horaria, fecha y hora límite, margen y tratamiento de movimientos tardíos; todavía no hay valores aprobados.

## Secuencia funcional propuesta

Conciliador prepara evidencia → solicita cierre → diagnóstico revisa catálogo de wallets esperadas, C0 y hallazgos → Coordinación Financiera verifica el expediente y autoriza/ejecuta el cierre → período se congela con auditoría. Si hay movimientos tardíos que afectan el cierre: solicitud justificada → Superadmin reabre → ajustes auditados → nueva conciliación y autorización de cierre.

**Nota:** el flujo de solicitudes, expediente/aceptación y cierre transaccional aún deben diseñarse/implementarse; las flechas no representan endpoints existentes.

## Reglas que el código ya verifica

- Diagnóstico de las **últimas ejecuciones existentes** por tipo/identidad, y detección de C0 bloqueado/descuadrado.
- Hallazgos de Wallets no resueltos de **cualquier gravedad**. Un hallazgo con `resuelto=True` no cuenta como pendiente, incluidos los resueltos por el sistema; la condición adicional de trazabilidad/evidencia debe probarse antes del cierre real.
- Aislamiento del período por empresa y permiso `conciliacion.ver` en la consulta.
- `puede_cerrar=false` deliberadamente, hasta cumplir las dependencias y contar con aprobación formal.

## Definiciones y controles pendientes

- Catálogo de wallets **esperadas y vigentes** por empresa/período, con altas/bajas y cobertura verificable. **No basta con contar ejecuciones existentes**.
- Regla de corte con zona horaria, hora límite, margen y contabilización de novedades tardías.
- Protocolo y soporte firmado por Finanzas; autorizaciones de excepción limitadas a incidencias sin permitir faltantes o C0 inválidos.
- Flujo de solicitud por conciliador y aprobación/cierre por Coordinación Financiera, con segregación de funciones y controles contra doble solicitud/ejecución.
- Congelación efectiva de escrituras financieras por período, verificación de carreras transaccionales, reapertura por Superadmin con motivo obligatorio y auditoría.
- Evidencia de resolución por sistema, snapshot de hallazgos, hashes y versión de reglas, sin exponer datos sensibles.
- Pruebas de seguridad, concurrencia, migraciones, regresiones privadas y aceptación funcional.

## Gate

**No fusionar una autorización de cierre funcional** hasta que estén implementados los bloqueos definitivos y aprobados formalmente por Finanzas y seguridad. El PR #144 mantiene un preflight de solo lectura; no abre rutas de cierre/reapertura ni modifica permisos.
