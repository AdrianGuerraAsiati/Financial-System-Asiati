# Reporte para Juanfe — decisiones pendientes de KPIs de Compras

**Objetivo:** cerrar únicamente las decisiones de negocio que todavía no se pueden deducir de la fuente o del tablero actual.

## Contexto ya resuelto técnicamente

Ya se implementaron dos familias monetarias independientes:

1. **Costo de compra** → `VALOR TOTAL COMPRA USD`.
2. **Valor comercial DDP** → `VALOR OCI (DDP)`.

La hoja derivada `Supply Chain` del snapshot actual usa una suma de `VALOR OCI (DDP)` agrupada por `ESTADO`, por lo que la plataforma puede reproducir esa lectura sin inventar una columna.

También se identificó la población usada por ese pivote actual:

- `EN BODEGA ASIATI SHENZHEN`
- `EN BODEGA ASIATI YIWU`
- `EN NACIONALIZACION`
- `EN OTM`
- `EN PRODUCCION`
- `ENVIADO A DESTINO`
- `PENDIENTE DEPOSITO`

La plataforma conserva ambas familias y no fuerza que una reemplace a la otra.

---

## Decisiones que necesitamos de negocio

### 1. KPI ejecutivo principal de Supply Chain

**Evidencia actual:** el tablero existente usa `VALOR OCI (DDP)`.

Confirmar:

- ¿el KPI ejecutivo principal debe seguir siendo **Valor comercial DDP**?
- ¿el **Costo de compra** debe mostrarse como KPI secundario/comparativo?
- ¿o ambos deben tener la misma jerarquía?

**No bloquea:** cálculo de ambas familias.  
**Sí bloquea:** nombre, orden y lectura ejecutiva del dashboard.

### 2. Confirmar la población “activa” del tablero

La población observada actual son los siete estados listados arriba.

Confirmar si ese conjunto sigue siendo la definición corporativa de **Supply Chain activo**.

Especialmente confirmar si deben incluirse en el futuro:

- `EN BODEGA ASIATI MIAMI`
- `ENVIADO A BODEGA ASIATI CHINA`
- `EN BODEGA PROVEEDOR`
- `PENDIENTE INVIMA`
- `EN RECLAMACION`
- `DEVOLUCION`

### 3. Definición de “valor en tránsito / valor en el mar”

No queremos inferir este KPI desde el nombre.

Indicar exactamente qué estados entran.

Opciones que la fuente permite separar:

- `ENVIADO A DESTINO`;
- `EN OTM`;
- `PENDIENTE DEPOSITO`;
- bodegas de origen;
- `EN NACIONALIZACION`;
- combinaciones de los anteriores.

También confirmar si el nombre “en el mar” aplica solo a `MARITIMO` o si corporativamente significa mercancía en tránsito sin importar transporte.

### 4. Qué familia monetaria usa “valor en tránsito”

Una vez definidos los estados del punto 3, confirmar cuál cifra se presenta:

- costo de compra;
- valor comercial DDP;
- ambas;
- otra métrica.

La plataforma ya puede calcular costo y DDP en paralelo sobre el mismo conjunto de estados.

### 5. EN OTM

Definir su significado logístico:

- tránsito;
- destino;
- etapa propia.

Aunque actualmente entra en la población monetaria del pivote, su `etapa_logistica` permanece `POR_DEFINIR`.

### 6. PENDIENTE DEPÓSITO

Definir si representa:

- destino;
- nacionalización/aduana;
- etapa propia.

Actualmente entra en la población monetaria observada, pero no se ha asignado una etapa.

### 7. PENDIENTE INVIMA

Definir si es:

- nacionalización;
- bloqueo regulatorio transversal;
- etapa propia.

Además confirmar si debe entrar en Supply Chain activo cuando aparezca.

### 8. OC parcialmente recibida

Si una OC tiene unas líneas `ENTREGADO` y otras abiertas:

- ¿la OC cuenta como activa?
- ¿se muestra como `MIXTA`, `PARCIAL` u otra etiqueta?
- ¿el conteo de “OCs activas” incluye cualquier OC con al menos una línea activa?

Los montos ya se calculan correctamente por línea; esta decisión afecta el conteo y la presentación de la OC.

### 9. Reclamaciones y devoluciones

Confirmar tratamiento económico de:

- `EN RECLAMACION`
- `DEVOLUCION`

Preguntas:

- ¿siguen representando valor económico expuesto?
- ¿se excluyen del Supply Chain activo?
- ¿se muestran como bloque independiente de riesgo/incidencia?

### 10. Valores faltantes o inválidos

La plataforma actualmente:

- no convierte faltantes a cero silenciosamente;
- suma solo valores válidos;
- reporta cuántas líneas quedaron sin valor o con valor inválido.

Confirmar política ejecutiva:

- ¿un KPI puede mostrarse con advertencia si hay faltantes?
- ¿o debe quedar bloqueado hasta corregir la fuente?

### 11. Granularidad de los valores monetarios

Confirmar que:

- `VALOR TOTAL COMPRA USD` es valor de **línea**, no un total de OC repetido en cada SKU;
- `VALOR OCI (DDP)` es valor de **línea**, no un total de OC repetido.

El tablero actual suma por filas, y la plataforma replica esa granularidad. Esta confirmación evita doble conteo si existe alguna excepción operativa.

### 12. Moneda

Los encabezados indican USD.

Confirmar si:

- todas las filas de estas dos columnas están efectivamente expresadas en USD;
- existen casos de otra moneda cargados sin conversión.

### 13. Pagado y saldo a proveedor

El Sheet actual contiene fechas de abono/pago, pero no se identificó una columna inequívoca con el monto de cada abono.

Necesitamos saber:

- ¿existe otra fuente con monto exacto de abonos?
- ¿dónde está?
- ¿cómo se asocia a OC/línea/proveedor?

Hasta tenerla, no se implementarán `pagado a proveedor` ni `saldo pendiente` en dinero.

---

## Respuesta mínima que desbloquea el siguiente dashboard

Con estas siete respuestas ya podemos cerrar la siguiente versión:

1. KPI ejecutivo principal: DDP / costo / ambos.
2. Estados exactos de Supply Chain activo.
3. Estados exactos de “en tránsito / en el mar”.
4. Familia monetaria de “en tránsito”.
5. Significado de `EN OTM`.
6. Significado de `PENDIENTE DEPOSITO`.
7. Tratamiento de OC parcial.

El resto puede cerrarse después sin bloquear el tablero principal.
