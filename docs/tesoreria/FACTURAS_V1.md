# Tesorería · Facturas de compra V1

Seguimiento: #134. La vista opera **cuentas por pagar**; los recaudos de clientes son un frente distinto.

## Identidad en interfaz — MVP
- La navegación presenta esta vista como **Facturación**, subtítulo **Cuentas por pagar**; el formulario se llama **Facturas de compra y pagos**.
- La implementación sigue siendo el submódulo `tesoreria` y conserva APIs, datos, permisos y reglas vigentes. El rótulo no crea un quinto motor ni implica emitir facturas electrónicas de venta.
- Se adjunta **factura de compra** al radicar la obligación. En un segundo paso, después del desembolso, se registran **fecha efectiva, importe y comprobante de pago**. La empresa se toma del selector autenticado y se valida en backend.
- Un **recibo distinto de la factura original o del comprobante bancario** no tiene contrato separado en V1: antes de añadir otro tipo documental debe identificarse la necesidad funcional, sin asumir que ambos soportes son equivalentes.

## Contrato implementado
- La fecha oportuna se toma **exclusivamente del vencimiento de la factura**. Si no está: PENDIENTE_VALIDACION. No se inventa fecha.
- El monto es el total a pagar de la factura; sin reglas de retenciones ni descuentos por ahora.
- El usuario registra el pago **manualmente después del desembolso** y adjunta PDF o imagen del comprobante real.
- Se admiten pagos parciales, preservando cada abono y soporte; el saldo y el estado se derivan.
- La V1 extrae campos de XML UBL con raíz Invoice; en PDF/JPG/PNG requiere captura manual y revisión. No incluye OCR ni XML DIAN AttachedDocument.
- Campos administrativos editables con auditoría; unidad de negocio, categoría y fijo/variable usan las listas activas del núcleo.
- Empresa y permisos se verifican en backend; TI tiene lectura sin mutación.
- Archivos privados en volumen `TESORERIA_DOCUMENTOS_DIR`; sin escritura a Google Sheets.

## Interfaz y notificaciones dentro del MVP

- El formulario de radicación está detrás del botón **Cargar factura** y se muestra en un diálogo accesible. Admite factura o foto de recibo PDF/PNG/JPG, y XML UBL. Se siguen exigiendo número o referencia y proveedor/tercero para identificar la obligación.
- En creación, **fecha prevista de pago = vencimiento indicado**; no significa desembolso realizado. La fecha de pago efectiva se registra únicamente al ingresar un abono real.
- Desde cada factura pendiente o parcial, el usuario autorizado abre un diálogo **Registrar pago y comprobante**: fecha efectiva, monto, referencia opcional y archivo del soporte. El saldo define PAGADA/PARCIAL/PENDIENTE según la lógica existente, sin cierre contable adicional.
- La bandeja conserva paginación y filtros por empresa y moneda; muestra estado de la factura y **avisos visuales** para vencidas, vence hoy, por vencer (7 días calendario) o sin vencimiento. La alerta no cambia el estado financiero.
- `GET /api/v1/tesoreria/notificaciones?empresa_id=...` retorna únicamente facturas de la empresa visible, con saldo positivo y vencimiento anterior o igual a hoy + 7 días. Resume cantidades por vencidas/próximas **sin sumar monedas distintas** y ofrece las primeras 20 ordenadas por fecha; el botón permite abrir la factura. No notifica obligaciones totalmente pagadas.
- Las alertas son **internas**, se actualizan al entrar, cambiar de empresa, consultar o registrar pago/factura. No se envían emails, WhatsApp ni notificaciones externas ni existe una tarea en segundo plano.
- Los botones de carga y pago requieren `tesoreria.facturas.gestionar` y `tesoreria.pagos.registrar` respectivamente. El acceso de solo lectura permanece intacto y se explica en pantalla.
- Esta funcionalidad sigue perteneciendo a Tesorería (CxP); la denominación **Facturación** es de interfaz y no añade un quinto motor.

## Fuera de alcance
Retenciones, descuentos, anticipos, notas crédito, conciliación bancaria automática, OCR universal y recaudos de clientes.

## Validación
`pytest tests/test_tesoreria_reglas.py tests/test_tesoreria_api.py tests/test_permisos_matriz.py`.

El equipo financiero debe validar datos de facturas reales, vencimientos, importes, pagos y soportes antes de aprobar el módulo. CI verde no es aceptación financiera.
