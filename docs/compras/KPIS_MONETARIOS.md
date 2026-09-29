# KPIs monetarios descriptivos — Compras / Supply Chain

**Estado:** implementado como familias descriptivas; pendiente definición de KPI ejecutivo oficial  
**Fuente:** `INFORME COMPRAS 2024-2026`  
**Granularidad:** línea/SKU  
**Moneda:** USD

## 1. Por qué existen dos familias

La fuente contiene dos columnas monetarias distintas y ambas responden preguntas válidas:

| Familia | Campo fuente | Pregunta |
|---|---|---|
| `costo_compra` | `VALOR TOTAL COMPRA USD` | ¿Cuál es el costo de compra asociado a la mercancía? |
| `valor_comercial_ddp` | `VALOR OCI (DDP)` | ¿Cuál es el valor comercial OCI/DDP asociado a la mercancía? |

No se fuerza una equivalencia entre ambas.

La hoja derivada `Supply Chain` del snapshot analizado utiliza explícitamente una suma de `VALOR OCI (DDP)` agrupada por `ESTADO`. Esa evidencia justifica implementar la familia DDP para poder reproducir/comparar el tablero actual.

La familia de costo de compra se implementa en paralelo para conservar la lectura económica desde `VALOR TOTAL COMPRA USD`.

## 2. Población denominada `Supply Chain actual`

Para reproducir la población observada en el pivote actual, se incluyen exactamente estos estados fuente normalizados:

```
EN BODEGA ASIATI SHENZHEN
EN BODEGA ASIATI YIWU
EN NACIONALIZACION
EN OTM
EN PRODUCCION
ENVIADO A DESTINO
PENDIENTE DEPOSITO
```

Esta lista **no redefine** la etapa logística de los estados ambiguos.

En particular:

- `EN OTM` sigue con `etapa_logistica = POR_DEFINIR`;
- `PENDIENTE DEPOSITO` sigue con `etapa_logistica = POR_DEFINIR`.

El conjunto solo reproduce la selección monetaria del tablero actual.

Estados como `ENTREGADO`, `ANULADA` y `EN RECLAMACION` no hacen parte de este total activo observado, aunque permanecen disponibles en el desglose general por estado.

## 3. Fórmulas

Para cada línea `i`:

### Costo de compra activo

```
SUM(valor_total_compra_usd_i)
WHERE estado_normalizado_i IN ESTADOS_ACTIVOS_TABLERO_ACTUAL
```

### Valor comercial DDP activo

```
SUM(valor_oci_ddp_i)
WHERE estado_normalizado_i IN ESTADOS_ACTIVOS_TABLERO_ACTUAL
```

Los cálculos se hacen a nivel de línea. Nunca se multiplica ni replica un total de OC al agrupar.

## 4. Precisión monetaria

El motor:

- usa `Decimal`, nunca `float`;
- acepta formatos de fuente con punto/coma como separadores;
- devuelve montos API como texto decimal con dos posiciones;
- no convierte un valor inválido en cero silenciosamente.

Para cada familia se reporta:

- líneas evaluadas;
- líneas con valor;
- líneas sin valor;
- líneas con valor inválido;
- monto calculado.

## 5. Disponibilidad por fuente

`VALOR TOTAL COMPRA USD` y `VALOR OCI (DDP)` siguen siendo campos no críticos para la lectura estructural general.

Sin embargo, cada familia monetaria requiere su propia columna.

Ejemplo:

- si EC deja de tener `VALOR OCI (DDP)`, la familia DDP global queda `disponible=false`;
- la familia de costo puede continuar si `VALOR TOTAL COMPRA USD` sigue disponible;
- un filtro `pais=CO` solo exige la columna para CO.

Así se evita sumar parcialmente países sin avisar.

## 6. API

```
GET /api/v1/compras/kpis?empresa_id=<id>
GET /api/v1/compras/kpis?empresa_id=<id>&pais=CO
```

Respuesta conceptual:

```json
{
  "poblacion_supply_chain_actual": {
    "estados_incluidos": ["..."],
    "lineas_activas": 0
  },
  "familias": [
    {
      "codigo": "costo_compra",
      "campo_fuente": "valor_total_compra_usd",
      "activo": {"monto_usd": "0.00"}
    },
    {
      "codigo": "valor_comercial_ddp",
      "campo_fuente": "valor_oci_ddp",
      "activo": {"monto_usd": "0.00"}
    }
  ]
}
```

También se expone desglose:

- por estado;
- por país;
- total general de todas las líneas, separado del total activo.

## 7. Qué NO decide este bloque

Estas familias no resuelven:

- cuál debe ser el KPI ejecutivo principal;
- qué significa exactamente `valor en tránsito`;
- qué significa exactamente `valor en el mar`;
- si OTM pertenece a tránsito, destino o una etapa propia;
- si pendiente depósito pertenece a destino/nacionalización;
- pagado a proveedor;
- saldo pendiente a proveedor;
- criterio de cierre de una OC parcial.

Esas preguntas quedan en `REPORTE_DUDAS_JUANFE_KPIS.md`.
