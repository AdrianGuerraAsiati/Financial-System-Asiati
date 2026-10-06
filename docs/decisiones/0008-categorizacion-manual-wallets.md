# 0008 — Categorización manual de movimientos de wallets, listas administrables y clave estable de hallazgos

- Fecha: 2026-10-06
- Estado: Aceptada
- Decide: Juan Felipe Parra (reglas de negocio)
- Revisión técnica: Adrian Guerra (núcleo, migraciones)

## Contexto

Al conciliar septiembre en la plataforma, los movimientos que el motor no puede categorizar solo (texto nuevo de Dropi
o `requiere_revision`) llegaban a la bandeja sin datos útiles y sin forma de dejar su categoría. Además, volver a
conciliar la misma wallet con un archivo nuevo crea hallazgos nuevos: lo que el conciliador ya había revisado se pierde.

## Decisión

1. **Categorización manual.** Todo movimiento `SIN_CONCEPTO` o con `requiere_revision` lo categoriza el auxiliar de
   conciliación a mano, con las 7 dimensiones: ingreso/egreso, unidad de negocio, categoría, empresa, tercero,
   modalidad y fijo/variable. Aplica a Wiilog, Tiendas y Pagos. Si ninguna categoría sirve, escala al coordinador.
2. **Listas cerradas y administrables.** El auxiliar solo elige de listas. El único texto libre es el **tercero**.
   La empresa es la de la wallet (no se edita) y la modalidad es WALLET. El coordinador financiero y el superadmin
   agregan, renombran y desactivan valores desde la plataforma; nunca se borran, y todo cambio queda en auditoría.
   Los valores son globales (aplican a todas las empresas).
3. **Valores iniciales.**
   - Empresas: WIILOG, ASIATI, TIENDAS ASIATI, ORIGEN VITAL (las únicas).
   - Unidades de negocio: FF, UM, TIENDAS, PROVEEDURIA, TRANSFER INTERCOMPANY, CC, CW, CADENA AHORRO,
     LOGISTICA INTERNACIONAL, CSC WIILOG, CSC SEGURIDAD, CHIN-CHIN, HUGO, CSC FINANZAS, SAC, CSC ASIATI, CEDI,
     CROSSDOKING, TRANSPORTES.
   - Categorías: la unión de las del catálogo de wallets y la columna "Conceptos de Gastos" de
     `parametros_flujo_caja_20261006.xlsx`, sin "FALTA INGRESAR" ni "PRUEBA" y sin duplicados (comparando en
     mayúsculas, sin tildes y sin espacios sobrantes).
   - Fijo/variable: FIJO y VARIABLE.
   - Las columnas Ciudad y Estado del Excel son de tesorería y no se cargan.
4. **Catálogo de conceptos v2** (`catalogo_conceptos_wallets.json`). Solo cambian etiquetas y qué va a revisión;
   ninguna cifra de conciliación:
   - La unidad DROPSHIPPING deja de existir: pasa a TIENDAS. La categoría DROPSHIPPING se mantiene.
   - Flete marca blanca: INGRESO · FF · COMISIONES.
   - Retiro a banco (`RETIRO_SALDO`, en Wiilog `RETIRO_BANCARIO`): unidad vacía y a revisión.
   - Transferencias a `cuentas_destino_grupo`: unidad y categoría vacías.
   - Wiilog toma ingreso/egreso, unidad y categoría del catálogo común, en la fila del mismo texto de Dropi.
5. **La categorización no se puede perder al volver a conciliar** (requisito):
   - cada hallazgo tiene una clave estable: empresa + wallet + regla + `mov_id` (movimientos) u `orden_id` (órdenes);
   - si la clave ya existe, se actualiza la evidencia y se conservan estado, observaciones, escalamiento y
     categorización;
   - si el problema ya no aparece en el archivo nuevo, el hallazgo queda "resuelto por el sistema" con nota
     automática, sin borrar el historial;
   - si un hallazgo resuelto por el sistema reaparece, se reabre como DETECTADO con nota automática; si lo resolvió
     una persona y sigue apareciendo, se queda RESUELTO y solo se actualiza la evidencia;
   - la bandeja muestra los hallazgos vigentes; deja de hacer falta el filtro "última carga".

## Consecuencias

- El núcleo necesita dos cambios con migración (dueño: Adrian): la clave estable en `hallazgos` (con la nota de
  sistema en los mensajes) y la tabla de valores por dimensión con el permiso nuevo `dimensiones.gestionar`
  (superadmin y coordinador). `parametros.editar` no se usa porque es solo del superadmin y versiona parámetros de
  motor.
- La categorización se guarda como dato estructurado en la evidencia del hallazgo y su historia en la auditoría.
  No se crea la tabla de movimientos (sigue siendo del PR C de la auditoría de arquitectura).
- En septiembre, la regla de retiros agrega a la bandeja 5 movimientos por revisar en Menpros, 22 en Proveeduría,
  2 en Pagos y 0 en Recompra y Wiilog.
- Nota para el motor de bancos: el estado "PAGO HUGO" del Excel de tesorería no va.
