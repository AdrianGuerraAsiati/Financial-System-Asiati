# 0005 — Google Sheets de Compras es fuente de solo lectura

**Estado:** aceptada  
**Fecha:** 28 de septiembre de 2026  
**Ámbito:** Compras / Supply Chain

## Contexto

La operación corporativa de Compras y Supply Chain se gestiona actualmente en el Google Sheet:

`INFORME COMPRAS 2024-2026`

La plataforma financiera comenzará a consumir esa información para análisis, KPIs, alertas, proyecciones y vistas operativas.

Por ahora, la organización no ha decidido migrar, reemplazar ni rediseñar esa fuente.

## Decisión

Hasta nueva decisión corporativa, el Google Sheet `INFORME COMPRAS 2024-2026` se trata como una **fuente externa de solo lectura**.

La plataforma puede:

- leer hojas, rangos, filas y fórmulas ya calculadas cuando corresponda;
- normalizar valores internamente;
- calcular etapas, KPIs, alertas y proyecciones;
- persistir snapshots, hashes, metadatos de lectura y resultados derivados en sus propios componentes;
- detectar y reportar inconsistencias.

La plataforma **no puede**:

- escribir celdas;
- cambiar estados;
- corregir valores;
- insertar filas o columnas;
- agregar observaciones;
- modificar fórmulas;
- eliminar información;
- ejecutar write-back automático;
- usar permisos de edición como requisito de operación.

## Regla de diseño

El patrón permitido es:

```
Google Sheet (fuente)
        |
        | lectura
        v
snapshot / normalización interna
        |
        v
reglas de negocio
        |
        v
KPIs / hallazgos / vistas / proyecciones
```

Nunca:

```
plataforma -> corrección automática -> Google Sheet
```

Si la plataforma detecta una inconsistencia, debe conservar el dato original y emitir un resultado derivado, por ejemplo:

```
estado_origen = "ENVIADO A DESTINO"
etapa_calculada = "RECIBIDO"
hallazgo = "La fila tiene fecha de entrega a bodega pero el estado origen no fue actualizado."
```

El sistema no modifica `estado_origen`.

## Consecuencias técnicas

1. El adaptador de Google Sheets para Compras debe solicitar únicamente scopes de lectura.
2. No se implementan métodos `update`, `append`, `batchUpdate` ni equivalentes en el adaptador de Compras.
3. Las reglas de negocio deben trabajar sobre una representación interna desacoplada del Sheet.
4. Se debe conservar suficiente trazabilidad para relacionar un resultado con la hoja/fila/rango leído.
5. Los cambios hechos manualmente en el Google Sheet se reflejarán en una lectura posterior; la plataforma no los origina.
6. Si en el futuro se aprueba write-back, deberá existir una nueva decisión formal que reemplace esta.

## Relación con otros documentos

Esta decisión tiene precedencia sobre cualquier propuesta de Compras que implique modificar el Sheet.

Documentos relacionados:

- `docs/compras/SPEC_COMPRAS_SUPPLY_CHAIN.md`
- `docs/compras/ESTADOS_LOGISTICOS.md`
- `docs/compras/PREGUNTAS_NEGOCIO.md`
- `Ai_Handoff.md`
