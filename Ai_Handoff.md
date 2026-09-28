# AI Handoff — Plataforma Financiera ASIATI

**Última actualización:** 28 de septiembre de 2026  
**Repositorio:** `AdrianGuerraAsiati/Financial-System-Asiati`

---

## 1. Para qué existe este archivo

Este es el **estado operativo vivo** del proyecto para que Adrian, Juanfe, Claude Code u otra AI puedan retomar trabajo sin reconstruir contexto, duplicar trabajo o inventar reglas financieras.

Debe leerse junto con:

- `CLAUDE.md`
- `docs/SPEC_NUCLEO.md`
- la SPEC del motor o módulo que se esté trabajando
- `docs/decisiones/`

Este archivo **no reemplaza** las SPEC ni las decisiones formales. Si contradice una decisión formal, actualizar este handoff para reflejar la decisión vigente.

### Cuándo actualizarlo

Actualizar este archivo cuando ocurra cualquiera de estos eventos:

- merge de un PR que cambie el estado del proyecto;
- nueva decisión de negocio validada por Juanfe;
- cambio de fuente oficial;
- inicio/cierre de un frente importante;
- aparición o resolución de un bloqueante;
- cambio de responsabilidad entre Adrian y Juanfe.

Al terminar trabajo sustancial, una AI debe revisar si este handoff quedó desactualizado.

---

## 2. Roles

### Adrian Guerra — @AdrianGuerraAsiati

Responsable principalmente de:

- arquitectura técnica;
- integración de módulos;
- infraestructura, despliegue y CI;
- revisión y merge de PRs;
- módulos/producto;
- `app/core` cuando no exista un PR coordinado tocándolo.

### Juan Felipe Parra — @juanparra-code

**Líder de datos financieros y líder funcional del proyecto.**

Su papel clave es:

- definir y validar criterio financiero;
- resolver ambigüedades de negocio;
- decidir reglas oficiales;
- validar parámetros;
- identificar fuentes y dueños de proceso;
- revisar lógica de motores financieros.

Juanfe también desarrolla PRs puntuales, principalmente reglas/documentación de motores y componentes coordinados del núcleo.

**No inventar decisiones de negocio que le correspondan a Juanfe.** Si falta una definición, dejar `TODO(negocio)` y escalar la pregunta.

---

## 3. Estado actual de `main`

Al momento de esta actualización:

`main = dc39b7c5451bce5f8192bb11a94e5e783e281fd0`

Último cambio fusionado:

`feat(wallets): apply Wiilog parameters v2`

### PR #41 — motor de referencia Wiilog + Claude Code kit

Fusionado.

Incluyó:

- `CLAUDE.md`, comandos y reglas de trabajo con Claude Code;
- documentación y decisiones;
- motor puro de referencia de la wallet Wiilog;
- tests sintéticos;
- regresión contra septiembre 2026;
- regla de no subir datos reales de `fixtures/`.

### PR #42 — Wiilog integrado a la plataforma

Fusionado.

Primer vertical slice de conciliación:

`archivo -> C0 -> motor -> hallazgos persistidos -> consulta`

Incluye:

- recepción de Excel de órdenes + wallet;
- registro de cargas con hash;
- empresa/fuente/período;
- C0;
- ejecución del motor Wiilog;
- persistencia de hallazgos;
- consulta por empresa/período;
- rechazo de carga duplicada.

### PR #43 — parámetros Wiilog v2

Fusionado después de detectar que dos commits de Juanfe habían quedado fuera del squash del PR #41.

Decisiones vigentes:

- **Bucaramanga no cobra fulfillment**;
- Bogotá: FF 2.500;
- Bogotá 3.0: FF 3.250;
- Bogotá 2.0: tarifa por confirmar;
- Medellín 2.0: tarifa por confirmar;
- devolución sin recaudo: el FF debe cobrarse; si no llega se reclama;
- reverso de FF en órdenes rechazadas: correcto e informativo;
- cobro en una bodega que no debe cobrar: `COBRADO_NO_CORRESPONDE`.

---

## 4. Trabajo de Juanfe en curso

### PR #44 — usuarios, roles, empresas asignadas y permisos

Estado al crear este handoff: **abierto y mergeable**.

Título:

`feat(core): add users, roles, assigned companies and permissions`

Toca `app/core` y contiene, entre otros:

- usuarios/login;
- roles;
- empresas asignadas;
- matriz de permisos;
- Argon2;
- JWT en cookie segura;
- auditoría;
- registro de ingresos;
- escalamiento/respuesta de hallazgos;
- supervisión;
- migración `0013_usuarios_auth_auditoria`.

### Coordinación mientras #44 siga abierto

Evitar cambios estructurales paralelos en `app/core`, salvo necesidad explícita y coordinada.

Trabajar preferentemente en:

- lógica de negocio;
- contratos de datos;
- documentación funcional;
- módulos aislados;
- tests de dominio;
- análisis de fuentes.

Juanfe también continuará la conciliación de wallets de **Tiendas y ASIATI**.

---

## 5. Arquitectura y reglas que siguen vigentes

La plataforma es:

**núcleo común + motores/módulos especializados**

No crear sistemas separados por empresa.

> El motor es código; la empresa es dato/configuración.

Dominios principales:

1. conciliación;
2. cartera;
3. tesorería;
4. cierres/resultados;
5. compras / supply chain.

Reglas:

- no abstraer para motores que todavía no existen;
- no duplicar un motor por empresa;
- conservar el valor crudo/original cuando se normaliza;
- dinero sin `float`;
- datos reales nunca al repo;
- primero fuente + granularidad + regla + excepción + criterio de aceptación; luego UI.

---

## 6. Tres frentes grandes priorizados

### A. Automatización de órdenes de compra

Objetivo: convertir el flujo actual de compras/OC en un proceso estructurado y trazable **sin reemplazar todavía la fuente corporativa actual**.

Hallazgo importante:

Una OC no debe tratarse como una sola fila ni como un único proveedor/estado.

Modelo conceptual:

`OC -> línea/SKU -> proveedor -> estado/movimiento logístico`

La UI puede agrupar por OC, pero los cálculos deben respetar las líneas.

### B. Abonos a cartera + OCR + tipos de comprobante

Objetivo futuro:

`comprobante -> tipo -> OCR -> extracción -> propuesta de asociación -> validación -> abono -> saldo`

Antes de OCR, cerrar reglas de negocio:

- pago parcial/total;
- varios pagos para una obligación;
- un pago para varias obligaciones;
- anticipos;
- monedas;
- retenciones;
- diferencias;
- duplicados;
- documentos ambiguos/no asociables.

No mezclar:

- pagos de ASIATI a proveedor;
- pagos de cliente hacia cartera.

### C. Mercancía en tránsito / “valor en el mar”

Objetivo: responder cuánto valor económico está comprometido en mercancía aún no recibida.

No interpretar “en el mar” como únicamente marítimo.

Métricas potenciales, aún por definir:

- valor de compra en tránsito;
- valor DDP;
- valor pagado;
- saldo pendiente al proveedor;
- valor por etapa logística;
- llegadas proyectadas.

No elegir una sola como oficial sin definición de negocio.

---

## 7. Fuente oficial de Compras / Supply Chain

### Decisión vigente

Hasta nueva orden corporativa:

> **`INFORME COMPRAS 2024-2026` en Google Sheets es la fuente operativa oficial y de solo lectura para la plataforma.**

El Excel exportado con el mismo nombre sirve como fotografía para análisis, pero el sistema debe trabajar contra el Google Sheet.

Por ahora **no**:

- rediseñar la fuente;
- migrarla a otra solución;
- exigir cambios a operación;
- escribir de vuelta al Sheet;
- sustituirla por una base nueva.

Patrón:

`Google Sheet actual -> lectura -> snapshot/control -> lógica -> resultado`

Decisión formal: `docs/decisiones/0005-compras-google-sheets-solo-lectura.md`.

---

## 8. Estructura conocida del Sheet de compras

### Hojas principales de detalle

- `INFORME CLIENTES (CO)`
- `INFORME CLIENTES (EC)`
- `INFORME CLIENTES (CL)`

Son las fuentes operativas detalladas y trabajan a nivel de línea/producto.

### Catálogos / auxiliares

- `PARÁMETROS`
- `SKU WIILOG`

### Vistas derivadas / control

- `REPORTE OC`
- `INFORME CORP`
- `INFORME E-COMM`
- `Supply Chain`
- `Supply Chain Wiilog`
- `OPERACION X CLIENTE`
- `RESUMEN`
- `KPIs`
- `Calc_Data`
- `Dashboard_Final`

Las vistas existentes sirven para entender y validar el negocio, pero **no se convierten automáticamente en source of truth**.

Regla recomendada:

`detalle -> nuestra regla -> resultado -> comparación contra vista existente`

---

## 9. Hallazgos relevantes del Sheet

- La granularidad principal es línea/producto.
- Existen OCs con múltiples proveedores.
- Existen OCs con líneas en distintos estados.
- Existen OCs con más de un modo de transporte.
- No calcular una OC completa asumiendo que todas sus líneas están en la misma etapa.
- Hay variantes textuales que deben normalizarse (por ejemplo marítimo con diferentes grafías), conservando siempre el valor original.

Patrón:

- `estado_origen`
- `etapa_logistica_calculada`

---

## 10. Dirección funcional del tablero de Compras / Supply Chain

Se busca una experiencia parecida al actual **Tablero de cartera**, pero con lógica propia de compras.

Copiar el patrón de interacción, no las métricas:

- pestañas;
- KPIs;
- filtros;
- puntos de atención;
- gráficos filtrables;
- tablas detalladas;
- drill-down.

### Navegación candidata

Aún no definitiva:

- Panel principal
- Órdenes de compra
- En producción
- En tránsito
- Nacionalización
- En bodega
- Proyección de llegadas
- Proveedores

### KPIs candidatos

No implementar hasta definir fórmula exacta:

- valor de compras abiertas;
- valor en producción;
- valor en tránsito;
- valor en nacionalización;
- valor recibido;
- pagado a proveedores;
- pendiente por pagar;
- órdenes activas;
- próximas ETA.

Cada KPI debe declarar:

- pregunta;
- población incluida;
- granularidad;
- columna monetaria;
- fórmula;
- exclusiones;
- tratamiento de nulos;
- ejemplo real.

---

## 11. Compras / Supply Chain — trabajo funcional iniciado

Mientras el PR #44 siga abierto, el frente activo fuera de `app/core` es Compras / Supply Chain.

Ya existen en la rama/PR de documentación:

- `docs/compras/SPEC_COMPRAS_SUPPLY_CHAIN.md`
- `docs/compras/ESTADOS_LOGISTICOS.md`
- `docs/compras/PREGUNTAS_NEGOCIO.md`

Baseline levantado del snapshot `INFORME COMPRAS 2024-2026.xlsx`:

- 2.259 líneas sustantivas entre CO, EC y CL;
- 705 OCs válidas por país;
- 214 OCs con más de un proveedor;
- 32 OCs con más de un estado;
- 46 OCs con más de un modo de transporte;
- estados y modos de transporte reales inventariados.

Principio funcional confirmado por el levantamiento:

`OC -> múltiples líneas/SKU -> proveedor/estado/transporte por línea`

No modelar la OC como una sola fila.

### Próximo paso

Resolver con Juanfe las preguntas priorizadas en `docs/compras/PREGUNTAS_NEGOCIO.md`, empezando por:

1. `EN OTM`;
2. `PENDIENTE DEPÓSITO`;
3. `PENDIENTE INVIMA`;
4. definición corporativa de valor en tránsito;
5. columna monetaria oficial del KPI.

Después de esas respuestas se puede cerrar el mapa de estados y definir el primer KPI implementable.


### Paso 1 — contrato funcional de fuente

Mapear las columnas exactas para:

- OC;
- país;
- cliente;
- comercial;
- proveedor;
- SKU;
- producto;
- cantidad/unidad;
- valor de compra;
- valor DDP;
- moneda;
- estado;
- transporte;
- documento;
- ETD;
- ETA;
- nacionalización;
- llegada a bodega;
- pagos/abonos al proveedor.

### Paso 2 — clasificación logística

Extraer **todos los estados reales** de las hojas principales y mapearlos a una etapa superior.

Categorías candidatas:

- `PRODUCCION`
- `TRANSITO`
- `DESTINO`
- `NACIONALIZACION`
- `RECIBIDO`
- `CERRADO`
- `EXCLUIDO`

Ejemplo inicial, no definitivo:

| Estado origen | Etapa candidata |
|---|---|
| EN PRODUCCIÓN | PRODUCCION |
| PENDIENTE DESPACHO | PRODUCCION |
| ENVIADO A DESTINO | TRANSITO |
| EN OTM | DESTINO |
| PENDIENTE DEPÓSITO | DESTINO |
| EN NACIONALIZACIÓN | NACIONALIZACION |
| EN BODEGA ASIATI | RECIBIDO |
| EN BODEGA WIILOG | RECIBIDO |

Validar todos los estados antes de codificar.

### Paso 3 — puntos de atención

Candidatos:

- ETA vencida y no recibida;
- enviada sin ETA;
- enviada sin documento;
- producción atrasada;
- OC parcialmente recibida;
- llegada registrada con estado incompatible;
- saldo pendiente a proveedor con mercancía avanzada.

Formato de regla:

`codigo -> condición -> severidad -> mensaje -> evidencia`

---

## 12. Decisiones abiertas

### Compras / Supply Chain

- estados exactos que componen mercancía en tránsito;
- columna monetaria de cada KPI;
- valor de compra vs DDP vs pagado vs comprometido;
- definición de OC cerrada;
- OCs parcialmente recibidas;
- atraso de producción;
- ventana de próximas llegadas.

### Cartera / OCR

- tipos oficiales de comprobante;
- aplicación a obligaciones;
- pagos parciales/múltiples;
- pago para varias obligaciones;
- monedas;
- retenciones;
- diferencias;
- duplicados;
- documentos no asociables.

### Wiilog

No inventar:

- tarifa Bogotá 2.0;
- tarifa Medellín 2.0;
- resolución operativa de ciertos duplicados/diferencias;
- fuentes complementarias de órdenes fuera de reporte.

---

## 13. Regla de cierre para cualquier AI

Antes de implementar una pantalla o automatización nueva:

1. identificar fuente oficial;
2. definir granularidad;
3. escribir regla;
4. escribir fórmula;
5. definir excepciones;
6. definir criterio de aceptación;
7. probar contra datos conocidos;
8. solo entonces construir UI/integración.

Si falta criterio financiero: **parar, documentar la pregunta y pedir definición a Juanfe.**
