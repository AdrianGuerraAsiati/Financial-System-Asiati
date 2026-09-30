# Estado de desarrollo · 30 de septiembre de 2026

Este documento es el handoff corto para **Juan Felipe, Adrian y Claude Code**. Resume el estado vigente después de la limpieza de PRs y del despliegue temporal de Compras con Excel en AWS.

## Pull requests

- **#86 · security(wallets)**: fusionado. Los identificadores operativos de la wallet Wiilog y los baselines reales dejan de vivir en el estado actual del repositorio. El identificador principal se inyecta por runtime mediante `WIILOG_WALLET_PRINCIPAL_EMAIL`; los baselines reales viven fuera de Git.
- **#80 · docs(cartera)**: cerrado como superado. Su fotografía documental quedó atrás respecto al bloqueo actual de Google y al estado de Cartera.
- **#81 · docs(core/wallets audit)**: cerrado como superado. Fue útil como auditoría histórica, pero quedó atrás después de #89, #91 y los cambios de infraestructura.
- **#91 · movimientos y categorización compartida**: es el único PR funcional que debe permanecer abierto y continúa en **draft**. Su CI está verde en el head revisado.
- **#92–#95**: fusionados. Implementan y corrigen el workaround de Compras con Excel local, sincronización desde S3 y generación del snapshot de desarrollo.

## Decisión pendiente de #91

El punto que no debe resolverse por inferencia es la semántica de `movimientos.tipo`.

La SPEC histórica lo trata como obligatorio, pero un movimiento `PENDIENTE` puede no tener todavía clasificación. Además, Wallets separa el tipo crudo `ENTRADA/SALIDA` de la dimensión contable `ingreso_egreso`.

El draft actual usa `movimientos.tipo` como dimensión contable, nullable mientras el movimiento está `PENDIENTE`, y conserva el tipo crudo dentro de `crudo`.

**No fusionar #91 hasta que Juanfe/Claude validen explícitamente ese contrato.**

## Desarrollo en AWS

El entorno de desarrollo sigue en AWS Lightsail y el frontend/API continúan publicados por HTTPS.

Mientras no tengamos resuelto el acceso administrativo de Google Cloud, Compras usa este flujo temporal:

```text
Excel original -> S3 privado -> copia operacional persistente en Lightsail
              -> backend Compras -> snapshot PostgreSQL -> dashboard
```

S3 es la fuente permanente temporal. Lightsail solo conserva una copia operacional read-only fuera del directorio de releases, por lo que sobrevive despliegues.

El deploy compara el ETag del objeto de S3. Si el Excel no cambió, no lo vuelve a preparar/copiar. Si cambió, regenera la copia operacional antes de desplegar.

## Snapshot actual de Compras

La carga validada de desarrollo quedó en modo `EXCEL_LOCAL` con esquema válido:

- snapshot persistido: **#2**;
- líneas totales: **2.260**;
- Colombia: **2.085**;
- Ecuador: **76**;
- Chile: **99**;
- campos críticos faltantes: **0**.

El dashboard ya puede consumir esta evidencia desde PostgreSQL sin leer el Excel en cada F5.

## Google Sheets

La integración directa con Google Sheets queda **pospuesta, no descartada**.

El bloqueo actual es administrativo en Google Cloud: necesitamos los permisos/cuenta administrativa adecuados para dejar el proyecto y la identidad de servicio configurados sin pelear contra políticas heredadas de otra organización.

Hasta que eso quede resuelto, **no se genera ni se versiona ningún JSON de service account**. El Excel en S3 es únicamente el mecanismo de desarrollo.

Cuando tengamos acceso, Compras volverá a Google Sheets read-only y conservará el mismo patrón de snapshots; el dashboard no debe depender de una lectura directa de Google en cada request.

## Cartera

No usar `INFORME COMPRAS 2024-2026` como fuente de Cartera.

La fuente real de Cartera/Mora/Proyección sigue pendiente de identificación/configuración. El código de Cartera debe mantenerse separado del workaround de Compras.

## Wallets

#89 ya dejó integradas las reglas/catálogos de wallets de tienda y pagos.

Con #86 fusionado, cualquier ejecución real de Wiilog debe recibir `WIILOG_WALLET_PRINCIPAL_EMAIL` desde configuración segura de runtime. El valor real no debe volver a Git, documentación, issues o logs.

## Próximos pasos

1. Juanfe/Claude: revisar #91 y cerrar la decisión `tipo` vs `ingreso_egreso`/tipo crudo.
2. Adrian: provisionar el identificador de wallet Wiilog en runtime antes de ejecutar conciliaciones reales en el entorno desplegado.
3. Mantener Compras operando con S3 + copia local + snapshots mientras llega el acceso administrativo de Google Cloud.
4. Cuando Google quede habilitado, reemplazar la fuente temporal por Google Sheets sin romper el contrato de snapshots.
5. Identificar la fuente real de Cartera antes de configurar sus rangos o tocar reglas financieras.
