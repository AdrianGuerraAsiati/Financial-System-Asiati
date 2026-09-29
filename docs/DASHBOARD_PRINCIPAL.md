# Dashboard principal V1

**Estado:** implementado  
**Ruta web:** `Inicio`  
**API:** `GET /api/v1/dashboard/principal?empresa_id=<id>`

## Objetivo

Inicio responde tres preguntas:

1. ¿Cómo están los módulos que el usuario puede ver?
2. ¿Qué elementos requieren revisión?
3. ¿Dónde debe entrar para trabajar el detalle?

No reemplaza los dashboards de Cartera, Compras o Conciliación.

## Alcance V1

La V1 trabaja sobre **una empresa seleccionada**.

No existe todavía consolidación multiempresa en una sola cifra. El selector global de empresa determina el contexto del dashboard.

## Permisos

Inicio no introduce un permiso nuevo.

El backend compone únicamente módulos para los que el rol ya tiene permiso:

- `cartera.ver`
- `compras.ver`
- `conciliacion.ver`

Una empresa no asignada responde 404 antes de consultar fuentes.

La UI también oculta los accesos directos a módulos no visibles.

## Módulos

### Cartera

Muestra, cuando las fuentes están disponibles:

- cantidad de operaciones;
- cantidad de registros de mora;
- cantidad de proyecciones;
- comprobantes pendientes de auditoría.

Los comprobantes pendientes alimentan la bandeja transversal de atención.

La V1 no agrega montos de Cartera en Inicio porque no se definió un contrato específico para un KPI monetario transversal.

Si una fuente de Google Sheets de Cartera no está configurada, Inicio no falla completo: el estado de esa fuente aparece como `NO DISPONIBLE`.

### Compras / Supply Chain

Reutiliza contratos ya implementados:

- costo de compra USD de la población actual;
- valor comercial DDP de la población actual;
- OCs con al menos una línea en esa población;
- puntos de atención objetivos.

No cambia la definición de población actual ni crea `valor en tránsito`.

La bandeja transversal utiliza los puntos de atención existentes del módulo, sin severidades nuevas.

### Conciliación

Consulta el último período de la empresa y muestra:

- hallazgos abiertos;
- hallazgos críticos abiertos;
- rango del último período.

Los hallazgos abiertos del motor `conciliacion_wallets` pueden aparecer en la bandeja transversal.

Si no existe ningún período, el estado es `SIN EJECUCIONES`.

## Bandeja transversal “Requiere atención”

Contrato conceptual:

```
modulo
codigo
categoria
titulo
descripcion
referencia
url_destino
```

V1 usa categorías descriptivas ya soportadas por el origen, por ejemplo:

- `PENDIENTE`
- `DIFERENCIA`
- categorías técnicas/operativas de Compras.

La bandeja **no**:

- inventa severidades;
- calcula un score;
- ordena empresas por desempeño;
- decide prioridades financieras nuevas.

Se limita a 12 elementos para mantener Inicio legible.

## Estado de datos

Inicio expone disponibilidad por módulo/fuente.

Ejemplos:

- Compras: modo de fuente, fecha del snapshot y validez del esquema;
- Cartera: disponibilidad independiente de operaciones, mora y proyección;
- Conciliación: último período conocido.

Una fuente caída o no configurada no debe tumbar los demás módulos.

## Navegación

La navegación principal queda:

```
Inicio
Cartera
Compras
Wallets (vista dedicada pendiente)
Chin Chin (pendiente)
```

Desde las tarjetas y la bandeja se puede abrir Cartera o Compras cuando existe una vista dedicada.

Conciliación puede resumirse en Inicio antes de que exista su propia vista web.

## Límites deliberados

La V1 no implementa:

- consolidación “Todas las empresas”;
- health score financiero;
- ranking de empresas;
- semáforos arbitrarios;
- predicciones;
- un KPI monetario transversal entre módulos;
- severidad nueva para hallazgos;
- vista web dedicada de Conciliación.

Cualquiera de esos cambios necesita su propio contrato.
