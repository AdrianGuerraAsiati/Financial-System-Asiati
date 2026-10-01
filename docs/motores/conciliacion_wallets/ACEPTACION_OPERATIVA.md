# Aceptación operacional · Motor 01 Conciliación de Wallets

**Estado:** pendiente de ejecución.  
**Objetivo:** decidir si Wallets está listo para considerarse el primer motor cerrado de la plataforma.

Este documento no redefine reglas. Las fuentes de verdad siguen siendo:

- `WALLET_WIILOG.md`;
- `WALLETS_TIENDAS_Y_PAGOS.md`;
- `PANTALLA_WALLETS.md`;
- parámetros JSON versionados;
- paquete privado de regresión para datos reales.

No copiar datos operativos, identificadores reales, saldos, montos ni filas de evidencia a Git, PRs o logs.

## 1. Preconditions

- [ ] `main` desplegado en desarrollo con CI verde.
- [ ] HTTPS, `/health` y `/ready` responden.
- [ ] Cognito permite login de los usuarios de desarrollo y PostgreSQL conserva rol/empresas/permisos.
- [ ] Datos base de Wallets cargados: empresas, período, fuentes y catálogos esperados.
- [ ] `WIILOG_WALLET_PRINCIPAL_EMAIL` está configurado en runtime seguro.
- [ ] Los archivos privados de regresión están disponibles fuera de Git para quien ejecuta la aceptación.

## 2. Regresión antes de UI

Ejecutar las regresiones privadas/reales disponibles antes de usar la interfaz.

- [ ] Wiilog: `tests/wallet_wiilog/test_regresion_septiembre.py`.
- [ ] Tiendas/pagos: `tests/wallet_tiendas/test_regresion_tiendas_septiembre.py`.
- [ ] Ningún baseline cambia sin una decisión de negocio documentada.
- [ ] Si una regla aprobada cambia el resultado, actualizar juntos regla, decisión y baseline privado.

El criterio no es “se parece”: debe reproducir exactamente el baseline vigente del paquete privado.

## 3. Flujo UI por tipo de wallet

Ejecutar desde la pantalla Wallets con una empresa y período reales de desarrollo.

### Wiilog

- [ ] Seleccionar empresa/período/fuentes correctos.
- [ ] Cargar wallet + órdenes.
- [ ] C0 muestra saldo/integridad y cobertura.
- [ ] Si C0 bloquea, no aparecen resumen ni hallazgos de ejecución posterior.
- [ ] Si C0 pasa, resumen y bandeja corresponden a la regresión privada.
- [ ] Hallazgos nuevos incluyen gravedad legible y evidencia suficiente sin exponer secretos.

### Tienda

Ejecutar al menos una wallet DROPSHIPPER y una PROVEEDOR.

- [ ] El catálogo solo muestra wallets pertenecientes a la empresa seleccionada.
- [ ] C0 cuadra contra la regresión.
- [ ] Estados/reglas T1-T4 coinciden con la SPEC aplicable.
- [ ] `ORDEN_ANTERIOR_AL_REPORTE` se agrupa como un hallazgo informativo por carga.
- [ ] `NO_ENCONTRADA` queda agrupado según el contrato actual.
- [ ] Movimientos `requiere_revision` llegan a bandeja como REVISAR.

### Solo pagos

- [ ] Cargar únicamente wallet.
- [ ] C0 pasa contra la regresión.
- [ ] Todos los movimientos quedan categorizados por el catálogo actual o marcados para revisión.
- [ ] No se inventa cruce contra facturas: eso pertenece a Cartera.

## 4. Gestión de hallazgos

Probar con roles reales de desarrollo.

- [ ] Conciliador puede ver y ejecutar en sus empresas.
- [ ] Conciliador puede observar/marcar resuelto cuando tiene `hallazgos.gestionar`.
- [ ] Conciliador puede escalar cuando corresponde.
- [ ] Coordinación financiera puede responder un hallazgo escalado.
- [ ] TI mantiene lectura pero no obtiene facultades financieras que no le correspondan.
- [ ] Empresa no asignada devuelve 404 antes de exponer datos.

## 5. Guardas operativas

- [ ] Período cerrado impide nueva conciliación.
- [ ] Archivo duplicado se rechaza o reutiliza únicamente en los casos explícitamente definidos.
- [ ] Un C0 bloqueado no persiste resultados posteriores como si la conciliación fuera válida.
- [ ] Las cargas conservan hash e idempotencia.
- [ ] Toda acción humana relevante queda auditada.

## 6. Persistencia y limitación conocida

Hoy:

- hallazgos persisten;
- C0 + resumen de la última corrida se conservan en `sessionStorage`.

Validar explícitamente:

- [ ] Recargar la página y confirmar qué evidencia permanece.
- [ ] Confirmar que la UI comunica que el resumen es de la sesión actual.
- [ ] Registrar como deuda que la ejecución completa todavía no es una entidad persistente.

Esta limitación no debe ocultarse al firmar la aceptación.

## 7. Aceptación funcional

La aceptación la debe dar el equipo que concilia, no solo desarrollo.

- [ ] El conciliador confirma que los resultados representan correctamente la operación.
- [ ] Las diferencias que el equipo espera ver aparecen con la severidad/estado correctos.
- [ ] Los casos que no deben ser hallazgo no aparecen en la bandeja.
- [ ] Los mensajes indican qué hacer sin exigir conocimiento del código.
- [ ] Cualquier discrepancia se documenta como bug, cambio de parámetro o decisión de negocio; nunca se “corrige” el baseline silenciosamente.

## 8. Evidencia de cierre

Registrar fuera de datos sensibles:

- fecha de la corrida;
- commit desplegado;
- período;
- tipos de wallet probados;
- resultado PASS/FAIL por sección;
- nombres/roles de quienes aceptaron;
- referencias a issues/PRs de discrepancias.

## 9. Gate

**PASS:** todas las guardas críticas y la aceptación funcional están completas.  
**FAIL:** cualquier discrepancia en C0, baseline, permisos, integridad o regla financiera.

Solo con PASS se puede declarar “Motor 01 aceptado” y avanzar a endurecer el núcleo para el segundo motor.
