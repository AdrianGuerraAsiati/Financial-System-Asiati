# Auditoría de arquitectura · Core + Wallets

**Fecha:** 29 de septiembre de 2026  
**Base revisada:** `main` de `AdrianGuerraAsiati/Financial-System-Asiati`  
**Objetivo:** comparar la arquitectura objetivo del proyecto contra el código, migraciones, tests y documentación vigente, sin inventar reglas de negocio.

---

## 1. Conclusión ejecutiva

No se debe reconstruir el núcleo desde cero ni aplicar un DDL paralelo al repositorio actual.

`main` ya contiene un núcleo funcional y varios verticales integrados:

- autenticación, usuarios, roles, empresas asignadas y permisos;
- auditoría e historial de ingresos;
- empresas, fuentes, períodos, cierre/reapertura e historial;
- cargas con hash e idempotencia;
- hallazgos persistidos, escalamiento y mensajes;
- conciliación Wiilog integrada;
- Cartera;
- Compras / Supply Chain;
- dashboard principal;
- PostgreSQL + Alembic + Docker.

El principal trabajo pendiente del núcleo ya no es “crear la plataforma base”. Es completar las piezas necesarias para que los motores sean **reproducibles, trazables y reutilizables** sin duplicar reglas:

1. parámetros versionados persistidos;
2. entidad de ejecución de motor;
3. ciclo de vida y metadata de cargas;
4. movimientos/categorización compartidos;
5. registry explícito de módulos/motores;
6. exportación común donde realmente exista reutilización.

La lógica de Wiilog está más avanzada que lo indicado por documentos antiguos: fulfillment, flete, conceptos, C0 y una regresión de septiembre 2026 ya están documentados, implementados y cubiertos por tests.

---

## 2. Matriz de estado real

| Capacidad | Estado en `main` | Evidencia principal | Hueco real |
|---|---|---|---|
| Empresas | Implementado básico | `app/core/empresas.py` | Hoy solo persiste id/nombre. País, moneda y estado se agregan solo cuando un módulo los necesite. |
| Usuarios / auth | Implementado | `app/core/usuarios/`, `app/core/auth/`, migración `0013` | No recrear. |
| Permisos por empresa | Implementado | `app/core/permisos.py`, `usuario_empresas` | El rol es global por usuario y el alcance se limita por empresas, conforme a `ROLES_Y_PERMISOS.md`. |
| Auditoría | Implementado | `app/core/auditoria/`, migración `0013` | Ampliar por acción conforme aparezcan nuevas operaciones. |
| Períodos | Implementado | `app/core/periodos/` | La política exacta de qué bloquea un cierre sigue pendiente de negocio. |
| Cierre / reapertura | Implementado | `periodo_cierre_eventos`, servicios de período | Reapertura exige motivo; el código bloquea por críticos abiertos. |
| Fuentes | Implementado mínimo | `app/core/fuentes/model.py` | Falta metadata estructural: motor/tipo/configuración si se vuelve necesaria. |
| Cargas | Implementado mínimo | `app/core/cargas/` | Falta nombre de archivo, ubicación persistida, estado de procesamiento, metadata y resultado C0 persistido. |
| Idempotencia | Implementado | unique `empresa_id + contenido_hash` | Es más estricta que “fuente/período/hash”; revisar solo si aparecen falsos positivos reales. |
| Hallazgos | Implementado | `app/core/hallazgos/` | Existe flujo/escalamiento; no existe todavía la “memoria persistente” genérica definida en la SPEC. |
| Contrato Motor | Implementado provisional | `app/core/motor.py` | Sigue correctamente provisional hasta un segundo motor de conciliación. |
| Registry de motores | No implementado | `app/main.py` importa routers directamente | Conviene introducirlo cuando exista el segundo motor/registro real, no como abstracción vacía. |
| Parámetros versionados | No implementado en DB | Wiilog usa `parametros_wallet_wiilog.json` v2 | Prioridad alta: hoy una ejecución no queda ligada a la versión de parámetros persistida. |
| Ejecuciones de motor | No implementado | Wiilog persiste cargas + hallazgos | Falta entidad que ate ejecución, cargas, versión de parámetros, estado, métricas y error. |
| Movimientos comunes | No implementado | Wiilog trabaja con DataFrames transitorios | Necesario antes de bancos/categorización compartida/flujo de caja. |
| Categorización común | No implementada | La lógica Wiilog clasifica su DataFrame localmente | Debe implementarse en core cuando se cierre el contrato de las 7 dimensiones. |
| Export común | No implementado | Compras tiene export propio | No generalizar hasta tener al menos dos consumidores reales. |
| Wallet Wiilog | Implementado funcional | `app/motores/conciliacion_wallets/wiilog/` | Falta completar persistencia/reproducibilidad del resultado, no rehacer reglas. |
| Otras wallets | Pendientes | No hay motores equivalentes | Requieren sus contratos y catálogos reales. |

---

## 3. Wiilog: estado real

### Ya resuelto

La implementación actual cubre, como mínimo:

- lectura y normalización de exportaciones Dropi;
- C0 de saldo y controles de integridad;
- agrupación de órdenes antes del cruce;
- clasificación de conceptos de wallet;
- cruces neto cero;
- transferencias por SUPER ADMIN para revisión;
- fulfillment por bodega;
- excepción de Bucaramanga;
- tarifas confirmadas y tarifas pendientes;
- devoluciones sin recaudo;
- reversos de órdenes rechazadas;
- comisión de flete de marca blanca;
- hallazgos por duplicidad, diferencia de tarifa, no cobrado y cobro no correspondiente;
- persistencia de hallazgos;
- API protegida por permisos;
- rechazo de carga duplicada.

La fuente vigente de detalle es:

- `docs/motores/conciliacion_wallets/WALLET_WIILOG.md`;
- `docs/motores/conciliacion_wallets/parametros_wallet_wiilog.json`;
- código de `app/motores/conciliacion_wallets/wiilog/`;
- tests de `tests/wallet_wiilog/`.

### Tests

Existen tests sintéticos para reglas de Wiilog y un test de regresión contra los archivos reales de septiembre 2026.

Los archivos reales permanecen fuera de Git y el test se salta cuando no están presentes, conforme a la política del proyecto.

### Dos líneas base distintas

El repositorio contiene dos referencias que no deben mezclarse:

1. `tests/test_wallet_acceptance_baseline.py`: referencia histórica **1.555 no pagadas / 28 duplicadas / 80 huérfanas**. El test actual valida el helper de equivalencia con valores suministrados; no ejecuta el motor sobre esos archivos.
2. `tests/wallet_wiilog/test_regresion_septiembre.py`: regresión específica de **Wiilog septiembre 2026**, conectada al motor real y a fixtures locales.

Hasta mapear el dataset histórico de 1.555/28/80 contra una wallet concreta, no debe tratarse como la regresión vigente de Wiilog.

---

## 4. Riesgo P0: regla de cierre no formalmente decidida

El código actual impide cerrar un período cuando existen hallazgos críticos abiertos.

Sin embargo:

`docs/decisiones/0001-que-bloquea-un-cierre.md`

mantiene esa política como **Propuesta**, con decisión de negocio pendiente.

Esto produce una diferencia entre:

- comportamiento productivo codificado;
- estado formal de la decisión.

No cambiar el código por inferencia.

### Acción requerida

Juan Felipe debe cerrar la decisión 0001 indicando una de las políticas propuestas o una alternativa explícita.

Hasta entonces, cualquier cambio en la lógica de cierre es **BLOCKED BUSINESS**.

---

## 5. Qué queda de la propuesta de modelo físico hecha fuera del repo

La propuesta externa de DDL contenía ideas útiles, pero **no debe aplicarse como migración directa**.

### Se conserva conceptualmente

- versión de parámetros persistida;
- entidad de ejecución de motor;
- inputs de una ejecución;
- ciclo de vida de cargas;
- resultado C0 persistido;
- trazabilidad carga → ejecución → hallazgo/resultado;
- categorización en el núcleo;
- metadata estructurada de fuentes cuando haya necesidad real.

### Se descarta o adapta al repo actual

**No crear schema `core`.**  
La SPEC vigente usa `public` para el núcleo y schemas propios solo cuando un motor realmente los necesita.

**No migrar PK existentes a UUID.**  
El repo trabaja con enteros autoincrementales. No hay beneficio demostrado que justifique una migración masiva.

**No recrear roles/permisos.**  
Ya existe una decisión formal: un rol fijo por usuario + empresas asignadas + matriz de permisos en código.

**No crear hoy `wallets.orders` y `wallets.matches` solo porque aparecieron en un bosquejo.**  
Wiilog actualmente procesa órdenes en memoria y persiste hallazgos. Esas tablas deben aparecer cuando exista una necesidad persistente concreta: drill-down, reejecución sin volver a leer archivos, trazabilidad granular o reutilización.

**No inventar un modelo dinámico alterno de las siete dimensiones.**  
`SPEC_NUCLEO.md` define una forma concreta de movimientos/categorización. Si se quiere cambiar ese contrato, debe hacerse como decisión explícita antes de implementar.

---

## 6. Próximos PRs recomendados

### PR A · Reproducibilidad del motor

Agregar al núcleo:

- `parametros_versiones`;
- `ejecuciones_motor`;
- relación ejecución ↔ cargas;
- versión de parámetros usada;
- estado, inicio/fin, métricas y error;
- tests de que una ejecución puede reconstruir sus inputs.

**No cambiar reglas financieras.**

### PR B · Ciclo de vida de cargas y C0 persistido

Extender `cargas` con lo necesario para operación:

- nombre original;
- ubicación/identificador del archivo si se decide conservarlo;
- estado;
- metadata;
- validación;
- errores/advertencias C0.

El almacenamiento físico del archivo debe resolverse mediante una interfaz sustituible.

### PR C · Movimientos + categorización

Implementar solo cuando esté confirmado el contrato de las siete dimensiones:

- movimiento normalizado;
- crudo intacto;
- hash por fila;
- estado de categorización;
- regla aplicada;
- catálogo/importación de reglas;
- recategorización solo en períodos abiertos.

Este PR es prerequisito natural para conciliación bancaria y flujo de caja.

### PR D · Registry de módulos

Hoy `app/main.py` registra routers directamente.

Extraer un registry únicamente cuando el segundo motor haga evidente qué metadata debe declarar cada módulo. Evitar diseñarlo completo antes de ese momento.

---

## 7. Decisiones de arquitectura que permanecen correctas

1. Un solo sistema; la empresa es dato/configuración.
2. Monolito modular.
3. Un PostgreSQL.
4. El núcleo no conoce reglas específicas de Wallets.
5. El contrato `Motor` es provisional.
6. No se abstrae para motores que todavía no existen.
7. Dinero nunca se opera con `float`.
8. Los motores pueden operar en centavos enteros; la frontera persistente usa decimal exacto.
9. Los datos reales no se suben al repositorio.
10. Un período cerrado no se modifica sin reapertura auditada.

---

## 8. Resultado de esta auditoría

La prioridad técnica correcta ya no es “crear el core”.

La prioridad es:

**cerrar la decisión de cierre + hacer reproducibles las ejecuciones + persistir correctamente cargas/params + construir movimientos/categorización cuando su contrato esté listo.**

Wiilog debe continuar desde lo ya implementado. No debe reiniciarse a partir de documentos históricos.
