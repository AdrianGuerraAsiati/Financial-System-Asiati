# Estados logísticos — Compras / Supply Chain

**Fuente:** `INFORME COMPRAS 2024-2026`  
**Estado:** levantamiento inicial; no codificar las filas marcadas como pendientes sin validación.

---

## 1. Estados observados en las hojas de detalle

Snapshot analizado: CO + EC + CL.

| Estado origen | Líneas observadas | Lectura inicial |
|---|---:|---|
| ENTREGADO | 1.790 | operación recibida/entregada |
| ENVIADO A DESTINO | 284 | tránsito hacia destino |
| EN PRODUCCION | 67 | producción |
| PENDIENTE DEPÓSITO | 33 | ubicación exacta por validar |
| ANULADA | 27 | operación excluida/anulada |
| EN OTM | 17 | etapa exacta por validar |
| EN BODEGA ASIATI YIWU | 16 | mercancía en bodega de origen |
| EN BODEGA ASIATI SHENZHEN | 11 | mercancía en bodega de origen |
| EN RECLAMACION | 11 | incidencia, no describe por sí sola la ubicación física |
| EN NACIONALIZACION | 3 | nacionalización |

Total de líneas con estado observado: **2.259**.

---

## 2. Estados existentes en `PARÁMETROS` pero no observados en el detalle actual

El catálogo de la hoja `PARÁMETROS` también contiene:

- `DEVOLUCION`
- `EN BODEGA ASIATI MIAMI`
- `ENVIADO A BODEGA ASIATI CHINA`
- `PENDIENTE INVIMA`
- `EN BODEGA PROVEEDOR`

Deben mantenerse como valores válidos del universo de negocio aunque el snapshot actual no los esté usando en CO/EC/CL.

---

## 3. Mapa inicial: seguro vs pendiente

### 3.1 Mapeos de baja ambigüedad

| Estado origen | Etapa propuesta | Situación |
|---|---|---|
| EN PRODUCCION | PRODUCCION | NORMAL |
| EN BODEGA ASIATI YIWU | ORIGEN | NORMAL |
| EN BODEGA ASIATI SHENZHEN | ORIGEN | NORMAL |
| ENVIADO A DESTINO | TRANSITO | NORMAL |
| EN NACIONALIZACION | NACIONALIZACION | NORMAL |
| ENTREGADO | RECIBIDO | NORMAL |
| ANULADA | SIN_ETAPA | ANULADA |
| EN RECLAMACION | POR_DEFINIR | RECLAMACION |

Estos mapeos siguen siendo borrador funcional hasta aprobación, pero son los que presentan menor ambigüedad semántica.

### 3.2 Estados que requieren definición explícita

| Estado origen | Pregunta |
|---|---|
| EN OTM | ¿Se considera tránsito internacional, tránsito en destino o una etapa separada? |
| PENDIENTE DEPÓSITO | ¿La mercancía ya llegó al país? ¿Está antes, durante o después de nacionalización? |
| EN BODEGA ASIATI MIAMI | ¿Miami se trata como origen/hub, tránsito o una etapa separada? |
| ENVIADO A BODEGA ASIATI CHINA | ¿Sigue en producción/origen o ya se considera disponible para consolidación? |
| EN BODEGA PROVEEDOR | ¿Se considera producción terminada en origen o una etapa separada? |
| PENDIENTE INVIMA | ¿Es nacionalización, bloqueo regulatorio o incidencia transversal? |
| DEVOLUCION | ¿Es cierre, tránsito inverso o incidencia? |

No codificar estos estados dentro de una etapa superior hasta resolver la pregunta.

---

## 4. Propuesta de dimensiones

### Etapa logística

Candidatas:

- `PRODUCCION`
- `ORIGEN`
- `TRANSITO`
- `DESTINO`
- `NACIONALIZACION`
- `RECIBIDO`
- `POR_DEFINIR`
- `SIN_ETAPA`

### Situación operativa

Candidatas:

- `NORMAL`
- `ANULADA`
- `RECLAMACION`
- `DEVOLUCION`
- `BLOQUEO_REGULATORIO`

La ventaja de dos dimensiones es no perder ubicación logística cuando aparece una excepción.

---

## 5. Regla de mercancía en tránsito

**No está cerrada.**

Antes de calcular “valor en el mar” o “mercancía en tránsito” se debe decidir qué etapas entran.

Preguntas abiertas:

- ¿solo `TRANSITO`?
- ¿`ORIGEN + TRANSITO`?
- ¿incluye `DESTINO`?
- ¿incluye `NACIONALIZACION`?
- ¿se reporta por separado producción, tránsito y nacionalización?
- ¿qué pasa con líneas en reclamación?

La plataforma debe poder mostrar componentes separados aunque después exista un KPI consolidado.

---

## 6. Regla para OCs con estados mixtos

Una OC puede tener varias líneas con estados distintos.

Por tanto:

- no asignar a la OC un único estado por sobrescritura;
- el estado de una OC debe ser **derivado** de sus líneas;
- el valor por etapa se calcula por línea;
- la UI puede mostrar una etiqueta como `PARCIAL / MIXTA` cuando existan varias etapas.

La definición exacta de la etiqueta agregada de OC queda pendiente.

---

## 7. Criterios de aceptación futuros

Para cada estado normalizado se debe guardar al menos un ejemplo real del Sheet con:

- país;
- OC;
- SKU/línea;
- estado origen;
- etapa esperada;
- situación esperada.

Los ejemplos se usarán como regresión funcional cuando se implemente el lector de Google Sheets.
