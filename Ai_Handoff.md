# AI Handoff — Plataforma Financiera ASIATI

**Última actualización:** 29 de septiembre de 2026  
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

Estado funcional relevante de `main`:

- PR #44 fusionado: usuarios, roles, empresas asignadas, permisos, login, auditoría y supervisión.
- PR #48 fusionado: Cartera y Wiilog integrados al modelo común de autenticación/autorización.
- PR #50 fusionado: primer vertical read-only de Compras / Supply Chain.
- PR #51 fusionado: observabilidad de fuente, calidad, agrupación por OC y explorador web de Compras.
- PR #52 fusionado: familias monetarias descriptivas de costo de compra y valor comercial DDP.
- PR #53 fusionado: entorno local de un comando con migraciones, bootstrap de desarrollo y fuente sintética de Compras.
- Las APIs protegidas viven bajo `/api/v1`.
- El frontend cuenta con login, cambio obligatorio de contraseña, selector de empresa, logout, Cartera y explorador de Compras.

Head de `main` al actualizar este handoff:

`867e888f18c96bc18d7613509c90af63eaf7f914`

Último cambio fusionado:

`chore(dev): add one-command local bootstrap and compras demo`

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

## 4. Auth / permisos — estado integrado

### PR #44 — usuarios, roles, empresas asignadas y permisos

**Fusionado.**

Entregó el núcleo común de:

- usuarios/login;
- roles;
- empresas asignadas;
- matriz de permisos;
- Argon2;
- JWT en cookie;
- auditoría;
- registro de ingresos;
- escalamiento/respuesta de hallazgos;
- supervisión;
- migración `0013_usuarios_auth_auditoria`.

### PR #48 — integración de Cartera y Wiilog con auth

**Fusionado.**

Incluye:

- permisos propios `cartera.ver` y `cartera.comprobantes.subir`;
- validación de empresa asignada en Cartera;
- Cartera bajo `/api/v1/cartera/*`;
- Wiilog protegido con `conciliacion.ejecutar` y `conciliacion.ver`;
- Wiilog bajo `/api/v1/wallets/wiilog/*`;
- pantalla de login;
- cambio obligatorio de contraseña en primer ingreso;
- selector de empresa desde `/api/v1/auth/me`;
- logout;
- cookie de sesión configurable por entorno: desarrollo local puede usar no-Secure y producción debe usar `SESSION_COOKIE_SECURE=true`.

La excepción temporal de endpoints Wiilog sin autenticación (decisión 0004) quedó cerrada.

### Responsabilidad actual

La integración técnica de módulos con el núcleo común queda principalmente del lado de Adrian. Juanfe mantiene la validación funcional/financiera y puede continuar con conciliación de wallets de **Tiendas y ASIATI**.

---

## 4.1 Desarrollo local listo para previsualización

Una instalación limpia puede levantarse con:

```bash
docker compose up --build
```

El compose de desarrollo ejecuta automáticamente:

1. PostgreSQL;
2. `alembic upgrade head`;
3. bootstrap idempotente de empresa + superadmin;
4. API FastAPI.

Defaults exclusivamente locales:

- URL: `http://localhost:8000`
- usuario: `admin@asiati.local`
- contraseña: `AsiatiDev2026!`
- empresa inicial: `ASIATI Demo`

Los puertos de desarrollo se ligan a `127.0.0.1`.

Compras arranca por defecto con `COMPRAS_DEMO_MODE=true`, usando datos sintéticos claramente marcados como `DEMO LOCAL`. Producción rechaza ese modo.

Para usar Google Sheets real en desarrollo:

```bash
docker compose -f docker-compose.yml -f compose.google.yml up --build
```

con `COMPRAS_DEMO_MODE=false`, el spreadsheet ID y el service account configurados.

Guía: `DEV_SETUP.md`.

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

## 11. Compras / Supply Chain — vertical read-only + observabilidad

Compras / Supply Chain ya existe como módulo independiente en `app/motores/compras_supply_chain/`.

Documentación vigente:

- `docs/compras/SPEC_COMPRAS_SUPPLY_CHAIN.md`
- `docs/compras/ESTADOS_LOGISTICOS.md`
- `docs/compras/PREGUNTAS_NEGOCIO.md`
- `docs/compras/CONTRATO_FUENTE.md`
- `docs/compras/KPIS_MONETARIOS.md`
- `docs/compras/DASHBOARD_EJECUTIVO.md`
- `docs/compras/REPORTE_DUDAS_JUANFE_KPIS.md`
- `docs/decisiones/0005-compras-google-sheets-solo-lectura.md`

### Fuente y seguridad

La fuente oficial continúa siendo `INFORME COMPRAS 2024-2026` en Google Sheets.

Reglas implementadas:

- scope de Google Sheets: `spreadsheets.readonly`;
- no existen métodos de write-back en el adaptador;
- lectura de `INFORME CLIENTES (CO)`, `(EC)` y `(CL)`;
- permiso backend `compras.ver`;
- país, hoja y número de fila quedan en cada línea para trazabilidad.

### Contrato y drift

Existe un contrato técnico de encabezados.

Si falta un campo crítico o aparecen encabezados duplicados:

- `/compras/fuente/estado` sigue disponible para diagnóstico;
- los endpoints operativos se bloquean con 503;
- no se calculan resultados silenciosamente sobre un esquema degradado.

Campos críticos iniciales:

- OC;
- cliente;
- proveedor;
- estado;
- modo de transporte.

Los demás campos consumidos se reportan como esperados/no críticos.

### Snapshot/cache

La fuente usa un snapshot en memoria con TTL configurable:

`COMPRAS_SHEETS_CACHE_SECONDS=60`

El cache evita releer CO/EC/CL en cada request. No es una base de datos ni una nueva fuente de verdad.

`GET /api/v1/compras/fuente/estado?forzar_lectura=true` fuerza una nueva lectura y sigue siendo read-only.

### API actual

Todos requieren `compras.ver`:

- `GET /api/v1/compras/fuente/estado`
- `GET /api/v1/compras/catalogos`
- `GET /api/v1/compras/calidad`
- `GET /api/v1/compras/resumen`
- `GET /api/v1/compras/kpis`
- `GET /api/v1/compras/dashboard`
- `GET /api/v1/compras/atencion`
- `GET /api/v1/compras/validacion/tablero`
- `GET /api/v1/compras/export.zip`
- `GET /api/v1/compras/ocs`
- `GET /api/v1/compras/lineas`

`/resumen` solo expone conteos estructurales.

`/kpis` expone dos familias monetarias descriptivas y exactas con `Decimal`:

- `costo_compra` → `VALOR TOTAL COMPRA USD`;
- `valor_comercial_ddp` → `VALOR OCI (DDP)`.

La hoja derivada `Supply Chain` del snapshot usa `SUM de VALOR OCI (DDP)` por `ESTADO`, por lo que DDP reproduce la lectura monetaria existente. Costo de compra se mantiene en paralelo; no se consideran equivalentes.

### Calidad, puntos de atención y agrupación

Reglas de calidad observacionales implementadas:

- línea sin OC;
- cliente vacío;
- proveedor vacío;
- estado vacío;
- estado con etapa `POR_DEFINIR`;
- transporte vacío;
- transporte fuera del catálogo conocido;
- fecha de entrega a bodega con etapa todavía no recibida.

Puntos de atención objetivos implementados, sin severidad de negocio:

- `ENVIADO A DESTINO` sin documento;
- `ENVIADO A DESTINO` sin ETD;
- `ENVIADO A DESTINO` sin ETA;
- ETA vencida sin entrega;
- ETA no interpretable;
- entrega registrada con etapa abierta;
- OC con varios estados;
- OC con varios proveedores;
- OC con varios transportes.

Estas señales **no corrigen la fuente** y no afirman por sí solas un error financiero.

La agrupación por OC expone proveedores, estados, etapas y transportes observados, además de banderas de composición mixta.

No se asigna todavía un único estado agregado a una OC.

Las filas `N/A` o sin OC no se agrupan entre sí.

### Vista ejecutiva + explorador web

Existe una vista protegida de **Compras** en el shell web con:

- tarjetas ejecutivas descriptivas de costo, DDP, OCs con líneas en la población actual y observaciones;
- gráficos descriptivos por estado y transporte;
- panel de puntos de atención;
- validación read-only contra el pivote de la hoja derivada `Supply Chain`;
- exportación ZIP con CSVs de líneas, OCs, puntos de atención y KPIs;
- estado técnico de la fuente;
- líneas leídas;
- estado del snapshot/cache;
- conteos estructurales de OCs;
- diagnóstico por hoja;
- filtros de OC/proveedor/país;
- OCs mixtas;
- paginación;
- drill-down a líneas originales de una OC;
- observaciones de calidad;
- catálogos observados.

Los valores de compra y OCI DDP pueden verse a nivel de línea y ahora también se agregan como **dos familias descriptivas** en el explorador. No llamar a ninguna de ellas “valor en tránsito / en el mar” ni convertirla en KPI ejecutivo oficial sin validación de negocio.


La comparación contra `Supply Chain` usa `COMPRAS_SHEETS_SUPPLY_CHAIN_RANGE` y solo compara cuando puede identificar país, `ESTADO` y DDP sin adivinar. La hoja derivada es referencia de regresión, no source of truth.

### Baseline del snapshot analizado

- 2.259 líneas sustantivas entre CO, EC y CL;
- 705 OCs válidas por país;
- 214 OCs con más de un proveedor;
- 32 OCs con más de un estado;
- 46 OCs con más de un modo de transporte.

Modelo confirmado:

`OC -> múltiples líneas/SKU -> proveedor/estado/transporte por línea`

### Decisiones que siguen bloqueadas

No inventar ni cerrar por código:

1. significado logístico definitivo de `EN OTM`;
2. significado de `PENDIENTE DEPÓSITO`;
3. tratamiento de `PENDIENTE INVIMA`;
4. definición corporativa de “valor en tránsito / en el mar”;
5. qué familia monetaria usa ese KPI y cuál tiene jerarquía ejecutiva;
6. estado agregado/cierre de una OC parcial;
7. tolerancias de ETA y producción.

Las dos familias monetarias descriptivas sí están implementadas. Los estados ambiguos permanecen `POR_DEFINIR` y los KPIs corporativos que dependen de su significado siguen pendientes.

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
