# Estado de desarrollo · 6 de octubre de 2026

Esta es la fotografía operativa vigente del proyecto. Reemplaza como referencia diaria a las fotografías del
30-sep y 1-oct, que se conservan como historia. No reemplaza las SPEC ni los ADR de `docs/decisiones/`.

## Main y desarrollo

El núcleo compartido, autenticación y Motor 01 ya están integrados sobre `main`.

Cambios recientes relevantes:

- #109: Amazon Cognito para credenciales; PostgreSQL conserva autorización financiera.
- #113-#115: estabilización de Wallets y del deploy de desarrollo.
- #116: identificador privado de la wallet principal de Wiilog fuera de Git y resuelto en runtime.
- #117: estado/gravedad reales en bandeja, C0 en pesos, corte de órdenes visible y manejo claro de configuración.
- #118: el deploy deja visible el error real de SSH en `Wait for SSH`.
- #119: catálogo de conceptos v2 y evidencia completa para movimientos que requieren categorización manual.
- #120: clave estable de hallazgos, resolución/reapertura por el sistema y preservación de categorización humana.

El entorno de desarrollo continúa en AWS Lightsail con HTTPS y despliegue automático después de CI verde.

## Wallets · Motor 01

La regresión real de septiembre ya reproduce las cinco wallets validadas contra la línea base privada. El flujo actual
cubre empresa, período, fuente, carga, C0, conciliación, hallazgos y gestión humana.

La decisión de categorización manual quedó formalizada en
`docs/decisiones/0008-categorizacion-manual-wallets.md`:

- siete dimensiones: ingreso/egreso, unidad de negocio, categoría, empresa, tercero, modalidad y fijo/variable;
- el auxiliar selecciona de listas; el coordinador financiero administra esas listas;
- tercero es el único texto libre;
- la categorización no se puede perder al reconciliar de nuevo.

#119 deja la evidencia y el catálogo listos. #120 agrega la infraestructura de núcleo para conservar el trabajo humano,
pero los motores todavía deben conectarse a `sincronizar_hallazgos_motor()`.

### Próximo bloque de Wallets

1. Listas administrables de dimensiones y permiso `dimensiones.gestionar`.
2. Conectar Wiilog, Tiendas y Pagos a la sincronización por clave estable.
3. Pantalla de categorización manual.
4. Ejecutar y firmar el gate formal de aceptación operacional.

El protocolo de aceptación está en
`docs/motores/conciliacion_wallets/ACEPTACION_OPERATIVA.md`.

La regresión técnica verde no sustituye esa aceptación funcional.

## Autenticación

Cognito está activo en desarrollo. Roles, empresas, permisos, auditoría e ingresos siguen en PostgreSQL. El flujo de
recuperación de contraseña usa Cognito; la configuración operativa de correo pertenece a AWS y no se versiona en Git.

## Compras / Supply Chain

Compras V1 permanece funcional. En desarrollo sigue vigente:

`S3 privado -> copia operacional local en Lightsail -> snapshot PostgreSQL -> dashboard`

No usar el Excel de Compras como sustituto de una fuente de Cartera.

## Cartera

#101 continúa abierto como draft. Porta transporte/ETA y alertas heredadas, pero no está listo para merge:

- la fuente real sigue sin validarse;
- los umbrales heredados 50/35/30 % requieren aprobación de negocio;
- la rama está fuertemente divergida de `main` y sus checks corresponden a una base antigua.

No reactivar ese merge hasta validar fuente, contratos y umbrales, y luego rebasar contra `main`.

## Gate operativo

Motor 01 solo se declara cerrado cuando se complete el protocolo de aceptación con evidencia funcional. CI, regresión
y despliegue verde son requisitos necesarios, no sustitutos de la firma operativa.
