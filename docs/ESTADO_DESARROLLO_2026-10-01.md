# Estado de desarrollo · 1 de octubre de 2026

Este documento reemplaza como fotografía operativa a `docs/ESTADO_DESARROLLO_2026-09-30.md`.
No reemplaza las SPEC ni los ADR de `docs/decisiones/`.

## Main

El 1-oct quedó fusionado el PR #109, que mueve la autenticación de credenciales a Amazon Cognito en desarrollo y mantiene en PostgreSQL la autorización financiera: usuario local, rol, empresas, permisos, estado activo, auditoría e ingresos.

La arquitectura conserva `AUTH_PROVIDER=local|cognito` como rollback. MFA sigue fuera del alcance inicial.

## Wallets

El primer motor ya tiene un flujo funcional de plataforma:

`empresa -> período -> fuente -> carga -> C0 -> conciliación -> hallazgos -> observar/escalar/resolver`

Cambios relevantes ya fusionados:

- #102: observación y resolución de hallazgos.
- #103: wallets de tienda y pagos conectadas al backend común.
- #104: catálogos de períodos/fuentes y cargador de datos base.
- #105: pantalla operativa de Wallets y navegación desde Inicio.
- #106-#108: ruta segura para cargar datos base reales de Wallets desde S3 privado en desarrollo; la carga inicial ya fue ejecutada y el workflow volvió a ser manual.

### Qué falta para declarar Motor 01 cerrado

No basta con que CI esté verde. Falta ejecutar y firmar la aceptación operacional con datos reales desde la interfaz, conforme a la SPEC del motor.

El protocolo está en:

`docs/motores/conciliacion_wallets/ACEPTACION_OPERATIVA.md`

Deuda conocida: C0 y el resumen de la última conciliación se conservan en `sessionStorage`, mientras los hallazgos sí persisten. La ejecución completa todavía no es una entidad persistente/auditable.

## Núcleo de movimientos y categorización

El PR #91 (`movimientos` + `reglas_categorizacion` + siete dimensiones) fue cerrado sin merge el 1-oct.

No se encontró un reemplazo en `main`.

La decisión que debe cerrarse antes de reconstruir ese frente es el contrato entre:

- tipo crudo del movimiento (por ejemplo ENTRADA/SALIDA);
- dimensión contable `ingreso_egreso`;
- nulabilidad mientras el movimiento está `PENDIENTE`.

No resolverlo por inferencia. La categorización compartida sigue siendo núcleo, no una responsabilidad local de Wallets.

## Cartera

El core desacoplado de fuente sigue disponible en `main`: resúmenes, agrupación por OC, diagnósticos de negociación, contratos de Operaciones/Mora/Proyección y comprobantes.

La fuente real de Cartera sigue pendiente de identificación/configuración. No usar Compras como sustituto.

PR #101 permanece abierto en draft con transporte/ETA y alertas heredadas. Aunque su CI pasó, está divergido de `main` y contiene umbrales heredados pendientes de validación funcional. No fusionar antes de:

1. identificar la fuente real;
2. validar los contratos contra esa fuente;
3. validar los umbrales/reglas con negocio;
4. actualizar la rama contra `main`.

## Compras / Supply Chain

Compras V1 continúa cerrada funcionalmente.

En desarrollo sigue vigente el puente temporal:

`S3 privado -> copia operacional en Lightsail -> snapshot PostgreSQL -> dashboard`

La transición posterior a Google Sheets read-only no debe cambiar el contrato de snapshots ni hacer que el dashboard dependa de una lectura viva en cada request.

## Orden de trabajo vigente

1. Verificar despliegue/smoke de Cognito en desarrollo.
2. Ejecutar la aceptación operacional de Wallets.
3. Cerrar la decisión de contrato de movimientos/categorización y reconstruir ese núcleo desde `main`.
4. Persistir una ejecución de conciliación completa (C0 + resumen + cargas + hallazgos).
5. Si aparece la fuente real de Cartera, validarla y continuar ese frente.
6. Si Cartera sigue bloqueada por fuente, usar Bancos como segundo motor para probar qué abstracciones pertenecen realmente al núcleo.

## Regla de cierre

Motor 01 se considera cerrado solo cuando el equipo financiero confirme que la corrida real representa correctamente la operación y quede registrada la evidencia de aceptación. CI verde y pantalla funcionando son condiciones necesarias, no suficientes.
