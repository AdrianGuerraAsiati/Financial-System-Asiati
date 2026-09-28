# Preguntas de negocio — Compras / Supply Chain

**Objetivo:** concentrar únicamente decisiones que bloquean lógica.  
Cuando una respuesta quede validada, moverla a la SPEC o a una decisión formal y marcarla como cerrada aquí.

---

## A. Estados y etapas

### Q-COMPRAS-001 — EN OTM

**Pregunta:** ¿qué representa exactamente `EN OTM` dentro del recorrido?

Opciones a validar:

- tránsito;
- destino;
- etapa propia.

**Impacto:** valor en tránsito, tiempos logísticos, alertas y tablero.

### Q-COMPRAS-002 — PENDIENTE DEPÓSITO

**Pregunta:** ¿en qué momento físico/aduanero está la mercancía?

**Impacto:** clasificación entre destino, nacionalización y recibido.

### Q-COMPRAS-003 — PENDIENTE INVIMA

**Pregunta:** ¿se considera parte de nacionalización o una incidencia regulatoria transversal?

**Impacto:** KPI de nacionalización y puntos de atención.

### Q-COMPRAS-004 — bodegas intermedias

Definir significado de:

- `EN BODEGA ASIATI MIAMI`
- `ENVIADO A BODEGA ASIATI CHINA`
- `EN BODEGA PROVEEDOR`

**Impacto:** etapa `ORIGEN`, producción terminada y disponibilidad para embarque.

### Q-COMPRAS-005 — DEVOLUCION

**Pregunta:** ¿una devolución representa cierre, tránsito inverso o una incidencia que conserva la etapa previa?

---

## B. KPIs financieros

### Q-COMPRAS-006 — valor oficial de compra

Para `Valor de compras` y `Valor en tránsito`, ¿qué columna manda?

Candidatas de la fuente:

- `VALOR TOTAL COMPRA USD`
- `VALOR OCI (DDP)`

No son equivalentes.

### Q-COMPRAS-007 — valor pagado y saldo pendiente

¿Las columnas:

- `FECHA DE COMPRA EN CHINA (ABONO)`
- `FECHA PAGO TOTAL EN CHINA`

solo representan hitos de fecha, o existe en otra fuente el monto exacto de cada abono?

Con el Sheet actual no se observa una columna inequívoca con **monto de cada abono**.

**Impacto:** no calcular `pagado` ni `saldo pendiente` a partir de fechas únicamente.

### Q-COMPRAS-008 — “valor en el mar”

Definir si el KPI corporativo incluye:

- solo mercancía físicamente viajando;
- mercancía en origen ya lista;
- mercancía en puerto/destino;
- nacionalización.

Recomendación funcional: conservar KPIs separados y luego, si negocio lo requiere, un agregado.

---

## C. Órdenes de compra

### Q-COMPRAS-009 — OC parcialmente recibida

Si una OC tiene líneas entregadas y otras abiertas:

- ¿sigue siendo activa?
- ¿cómo debe aparecer en el tablero?
- ¿qué fecha se considera cierre?

### Q-COMPRAS-010 — líneas sin número de OC

En el snapshot existen:

- CO: 85 líneas `N/A` + 3 vacías;
- CL: 15 líneas `N/A`.

Definir si:

- son muestras/operaciones legítimas sin OC;
- son errores de calidad;
- requieren una llave alternativa.

No excluirlas silenciosamente.

### Q-COMPRAS-011 — estado agregado de OC

Cuando una OC contiene varias etapas, ¿qué etiqueta debe mostrar la cabecera?

Candidatas:

- `PARCIAL`;
- `MIXTA`;
- etapa más avanzada;
- etapa menos avanzada;
- sin estado agregado, solo distribución por líneas.

El cálculo financiero siempre debe permanecer a nivel de línea.

---

## D. Alertas

### Q-COMPRAS-012 — atraso de producción

Definir la regla.

Candidata:

```
hoy > fecha_entrega_proveedor_estimada
AND no existe fecha_fin_produccion
AND operación no está anulada/cerrada
```

Falta definir tolerancia y severidad.

### Q-COMPRAS-013 — ETA vencida

Definir si se genera alerta cuando:

```
ETA < hoy
AND etapa no es RECIBIDO
```

¿Existe una tolerancia de días?

### Q-COMPRAS-014 — enviada sin documento / ETA

¿Debe ser advertencia o hallazgo crítico una línea en `ENVIADO A DESTINO` sin:

- documento de transporte;
- ETD;
- ETA?

### Q-COMPRAS-015 — inconsistencias de fecha/estado

Ejemplo:

- fecha de entrega a bodega diligenciada;
- estado todavía `ENVIADO A DESTINO`.

Definir si la plataforma solo alerta o puede inferir/corregir visualmente la etapa.

Recomendación: **alertar; nunca modificar la fuente automáticamente por ahora.**

---

## E. Próxima sesión con Juanfe

Orden sugerido para cerrar decisiones:

1. EN OTM;
2. PENDIENTE DEPÓSITO;
3. PENDIENTE INVIMA;
4. definición de “valor en tránsito”;
5. columna monetaria oficial;
6. OC parcial;
7. reglas de ETA/producción.

Con esas respuestas se puede cerrar una primera versión de `ESTADOS_LOGISTICOS.md` y definir los primeros KPIs implementables.
