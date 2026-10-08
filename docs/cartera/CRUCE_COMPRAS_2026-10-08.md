# Auditoría read-only Cartera ↔ Compras — 8-oct-2026

## Propósito
Comprobar procedencia de registros de FC y PROYECCIONES sin convertir un
match textual en identidad contable, deuda, cobro o aplicación de pagos.

## Evidencia de los Google Sheets conectados (consulta puntual)
- Fuentes: CARTERA V1 (`FC`, `PROYECCIONES`) y
  `INFORME COMPRAS 2024-2026` (`INFORME CLIENTES (CO)`,
  `INFORME CLIENTES (EC)`, `INFORME CLIENTES (CL)`).
- Población operativa de ambas vistas: **1.037 filas** (453 FC + 584
  PROYECCIONES). De ellas, **23 no tienen OC utilizable** y **11 tienen OC
  pero SKU vacío o `N/A`**. Se mantienen para revisión, sin join automático.
- Hay **1.003 filas con OC y SKU utilizables**: **442 en FC** y **561 en
  PROYECCIONES**. Todas tienen al menos una candidata descriptiva en Compras.
- Sobre esas 1.003 filas, **957** coinciden en OC, SKU, cliente, documento,
  estado, descripción y DDP **numérico observado** (438 FC, 519 PROYECCIONES).
  **46** tienen DDP original no disponible (4 FC, 42 PROYECCIONES). No
  surgieron diferencias monetarias numéricas en las restantes líneas con llave.
- Si se incluye un SKU vacío o `N/A` como una cadena literal, aparecen
  1.014 líneas con OC y candidatas por `OC+SKU`. **Ese conteo grueso
  no equivale a un match de identidad de línea** y por eso el módulo las
  clasifica explícitamente como `CLAVE_INCOMPLETA`.
- Las OCs distintas con texto utilizable totalizan 322 entre ambas vistas.
  OC+SKU no constituye identificador maestro y puede repetirse.
- OC+SKU puede repetirse para líneas distintas: existen combinaciones
  multiplicadas en la fuente. El resultado `COINCIDE` de una búsqueda
  simple de OC+SKU NO es suficiente para asociar una obligación.

## Alcance del módulo `cruce_compras.py`
Función pura sobre registros ya leídos, sin Google API, base de datos, API HTTP,
escrituras, usuario real ni modificaciones financieras. Usa OC/SKU para
identificar candidatos y luego compara país (si se conoce), cliente, documento,
estado, descripción y DDP. Cada resultado conserva procedencia (hoja y fila).

Estados:
- `COINCIDE`: un solo candidato pasa todas las comprobaciones y tiene DDP.
- `MONTO_SIN_EVIDENCIA`: algún importe original no está disponible.
- `MONTO_DIFERENTE`: no coincide el DDP verificable.
- `AMBIGUO`: hay varias líneas indistinguibles.
- `ATRIBUTOS_DIFERENTES`: contradicción de país/cliente/documento/estado/descripción.
- `SIN_COINCIDENCIA`: no existe candidata por OC/SKU.
- `CLAVE_INCOMPLETA`: OC o SKU ausente / `N/A`.

## Decisiones y bloqueos
1. **No tratar Compras como fuente oficial financiera de Cartera por
   esta coincidencia histórica**. La comparación sirve para evaluación
   de cobertura y procedencia, no para establecer saldo.
2. Las 46 filas con DDP original sin evidencia no se rellenan silenciosamente.
   En Proyecciones hay además una columna distinta `VALOR OCI` que puede
   incluir correcciones del catálogo `Parametros`. Se necesita revisión
   de granularidad antes de agregar valores.
3. Para un join económico estable falta definir un identificador de
   **línea de obligación** que sobreviva cambios de SKU, OC y documento,
   además de versionamiento y aplicaciones de pagos.
4. El origen `ingresos_totales` sigue sin acceso directo y por tanto no
   se verificó histórico de modificaciones ni quién registró cada OC.
5. Este diagnóstico no se activa en el despliegue y no modifica los
   endpoints ni las reglas financieras existentes.

## Próximo gate
Probar el módulo con un snapshot privado y reversible, revisar discrepancias
de OC/SKU repetidas, confirmar con Finanzas el contrato de obligaciones y
decidir explícitamente si Compras opera como respaldo de lectura para Cartera.
Datos reales y listados privados deben quedarse fuera de Git.
