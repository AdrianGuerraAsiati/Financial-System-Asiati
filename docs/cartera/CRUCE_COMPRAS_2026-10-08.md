# Auditoría read-only Cartera ↔ Compras — 8-oct-2026

## Propósito
Comprobar procedencia de registros de FC y PROYECCIONES sin convertir un
match textual en identidad contable, deuda, cobro o aplicación de pagos.

## Evidencia de los Google Sheets conectados (consulta puntual)
- Fuentes: CARTERA V1 (`FC`, `PROYECCIONES`) y
  `INFORME COMPRAS 2024-2026` (`INFORME CLIENTES (CO)`,
  `INFORME CLIENTES (EC)`, `INFORME CLIENTES (CL)`).
- FC: 447 filas con OC identificable, 135 OCs. Todas tienen correspondencia
  de OC+SKU en Compras y las 447 coinciden estrictamente también en DDP crudo,
  cliente, documento y estado.
- PROYECCIONES: 567 filas con OC identificable, 197 OCs. Todas tienen
  correspondencia de OC+SKU y estado en Compras. En 525 coincide además
  el DDP crudo; en otras 42 el DDP crudo es nulo en Proyecciones, aunque su
  línea tiene importe en Compras.
- Total: 1.014 filas con OC identificable, 322 OCs distintas sin sumar
  dos veces las OCs comunes, 972 matches estrictos de atributos e importe
  y 42 pendientes de evidencia monetaria.
- La lectura excluyó las filas con OC vacía o `N/A`; no se considera una llave
  maestra. Las vistas incluyen filas de muestras y registros sin OC que
  requieren análisis separado.
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
2. Las 42 filas con DDP original nulo no se rellenan silenciosamente.
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
