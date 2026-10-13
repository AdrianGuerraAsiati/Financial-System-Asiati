# Tesorería · Facturas de compra V1

Seguimiento: #134. La vista opera **cuentas por pagar**; los recaudos de clientes son un frente distinto.

## Contrato implementado
- La fecha oportuna se toma **exclusivamente del vencimiento de la factura**. Si no está: PENDIENTE_VALIDACION. No se inventa fecha.
- El monto es el total a pagar de la factura; sin reglas de retenciones ni descuentos por ahora.
- El usuario registra el pago **manualmente después del desembolso** y adjunta PDF o imagen del comprobante real.
- Se admiten pagos parciales, preservando cada abono y soporte; el saldo y el estado se derivan.
- La V1 extrae campos de XML UBL con raíz Invoice; en PDF/JPG/PNG requiere captura manual y revisión. No incluye OCR ni XML DIAN AttachedDocument.
- Campos administrativos editables con auditoría; unidad de negocio, categoría y fijo/variable usan las listas activas del núcleo.
- Empresa y permisos se verifican en backend; TI tiene lectura sin mutación.
- Archivos privados en volumen `TESORERIA_DOCUMENTOS_DIR`; sin escritura a Google Sheets.

## Fuera de alcance
Retenciones, descuentos, anticipos, notas crédito, conciliación bancaria automática, OCR universal y recaudos de clientes.

## Validación
`pytest tests/test_tesoreria_reglas.py tests/test_tesoreria_api.py tests/test_permisos_matriz.py`.

El equipo financiero debe validar datos de facturas reales, vencimientos, importes, pagos y soportes antes de aprobar el módulo. CI verde no es aceptación financiera.
