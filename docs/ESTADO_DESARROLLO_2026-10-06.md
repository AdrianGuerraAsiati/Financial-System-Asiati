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
- #121: listas administrables de las dimensiones de categorización, permiso `dimensiones.gestionar` y pantalla Parámetros.
- #122: categorización manual de Wallets conectada de punta a punta, sincronización por clave estable y bandeja de vigentes.
- #123: empaquetado y siembra idempotente de las listas iniciales de dimensiones durante el deploy de desarrollo.

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

#119-#122 completan el flujo de categorización manual: evidencia y catálogo, persistencia por clave estable, listas
administrables y formulario de las 7 dimensiones. Wiilog, Tiendas y Pagos ya sincronizan hallazgos vigentes sin perder
estado, observaciones, escalamiento ni categorización.

### Próximo bloque de Wallets

1. Resumen en tabla con indicador de avance e investigar el tiempo observado de conciliación (40–56 s).
2. Corte/cierre de período con el margen operativo acordado.
3. Ejecutar y firmar el gate formal de aceptación operacional.

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

#101 fue cerrado sin merge por obsoleto. Su contenido queda como referencia histórica, pero no debe rebasarse como
bloque: estaba muy divergido y conserva umbrales heredados 50/35/30 % sin validar.

Cuando Cartera retome, partir de `main` vigente, identificar/validar la fuente real y reaplicar únicamente las piezas de
transporte/ETA y alertas que negocio confirme.

## Gate operativo

Motor 01 solo se declara cerrado cuando se complete el protocolo de aceptación con evidencia funcional. CI, regresión
y despliegue verde son requisitos necesarios, no sustitutos de la firma operativa.
