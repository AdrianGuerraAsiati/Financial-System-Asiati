# Entrega 1 · Tablero operativo de Facturas de compra

**Implementación propuesta:** nueva consulta paginada, indicadores en backend y exportación a Excel, encima del modelo existente de Tesorería. No crea migraciones ni modifica registros.

## Bandeja y filtros

Se mantienen las facturas asociadas a una única empresa y a una única moneda en cada consulta. La lista muestra hasta 25 por página en UI (API permite 1–200 por página) y un total completo para navegación; ya no depende del corte fijo de 500 de la bandeja anterior.

Filtros: moneda (COP/USD/CLP), texto de factura/proveedor/descripción, estado derivado, categoría y rango de fechas de vencimiento. Las fechas son inclusivas. Los estados corresponden al cálculo existente: `PAGADA`, `PARCIAL`, `PENDIENTE`, `VENCIDA`, `PENDIENTE_VALIDACION`. Una factura parcial vencida mantiene estado `PARCIAL` y alerta `VENCIDA`.

## Indicadores

Los KPIs corresponden a **toda la empresa y moneda seleccionadas**, con independencia de los filtros de la tabla:

- **Pendiente:** suma de `monto_factura - abonos` para obligaciones con saldo positivo.
- **Vencido:** saldo pendiente de obligaciones con vencimiento anterior a hoy.
- **Por vencer:** saldos de obligaciones con vencimiento entre hoy y los próximos **7 días calendario**, inclusive. **Es un horizonte visual fijo y no una tolerancia de pago.**
- **Pagado en el período:** suma de abonos cuya **fecha real de pago** cae en las fechas seleccionadas; por defecto desde el primero del mes corriente hasta hoy, inclusive.
- **Sin vencimiento:** facturas con saldo positivo y sin fecha de vencimiento.

No se suman divisas distintas ni se aplican tasas de cambio.

## Exportación `.xlsx`

El Excel corresponde a todos los registros **coincidentes con los filtros de la bandeja** (no solo la página visible). No exporta datos de otras empresas. Límite explícito: 10.000 facturas por archivo; si se supera, la API solicita acotar filtros y responde 413.

- Hoja `Facturas`: todas las columnas operativas disponibles, estados, alertas y saldos derivados. Fechas y montos con tipos de celda Excel, filtros automáticos, encabezados y columna congelada.
- Hoja `Pagos`: detalle de cada abono registrado para esas facturas, incluidos fecha efectiva, monto, referencia y nombre del comprobante; **no incluye el contenido de los archivos bancarios**.
- Los campos libres se protegen frente a **inyección de fórmulas** de Excel.
- Respuesta autenticada y con `Cache-Control: no-store`.

## Contrato HTTP

- `GET /api/v1/tesoreria/consulta-facturas?empresa_id=...&moneda=...&...`
- `GET /api/v1/tesoreria/indicadores?empresa_id=...&moneda=...&pago_desde=...&pago_hasta=...`
- `GET /api/v1/tesoreria/exportacion-facturas?empresa_id=...&moneda=...&...`

Los tres endpoints requieren `tesoreria.ver`, acceso a la empresa y fechas válidas. No se alteran los endpoints de radicación/pagos ya existentes.

## Gate técnico

`pytest -q tests/test_core_tesoreria_tablero.py tests/test_core_tesoreria_api.py tests/test_tesoreria_reglas.py`

Pendiente de aceptación con documentos reales de Tesorería: equivalencia del Excel con el libro operativo, revisión de la ventana informativa y claridad de estados. Una CI verde no equivale a aceptación financiera.
