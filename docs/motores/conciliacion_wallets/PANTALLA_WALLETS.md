# Pantalla de Wallets — propuesta

Versión 2 · 30-sep-2026 (decisiones de Juan Felipe incorporadas) · Rama `feat/wallets-en-plataforma` · Dueño de reglas: Juan Felipe Parra · Revisor: Adrian Guerra

Objetivo: que un conciliador use la conciliación de wallets desde la plataforma: elige empresa, período y wallet;
sube los archivos; ve si el saldo cuadra (C0); y revisa los hallazgos por gravedad dejando su observación.

Esta propuesta **no cambia reglas de negocio**. Las reglas siguen en `WALLET_WIILOG.md`, `WALLETS_TIENDAS_Y_PAGOS.md`
y sus JSON. Respeta la auditoría del 29-sep (`AUDITORIA_ARQUITECTURA_CORE_WALLETS_2026-09-29.md`, hoy solo en la rama
`docs/core-wallets-architecture-audit`, sin fusionar): no crea tablas de movimientos, parámetros versionados ni
ejecuciones de motor. Usa cargas, hallazgos (estado, escalar, responder, mensajes), períodos y permisos.

---

## 1. Cómo está hoy (lo que se leyó)

**Wiilog** (`wiilog/api.py`, `wiilog/integracion.py`, registrado en `app/main.py` con prefijo `/api/v1`):

1. `POST /wallets/wiilog/conciliar` (form multipart) con `conciliacion.ejecutar` sobre la empresa del form.
2. Verifica que el período sea de la empresa y esté abierto (`PeriodoCerradoError` → 409).
3. Registra dos cargas con hash (`registrar_carga`); si el hash ya existe para la empresa → 409 con mensaje.
4. Lee los Excel, corre el motor puro, guarda como hallazgo cada chequeo C0 que no está `EN_ORDEN`
   (crítico si `BLOQUEADO`). Si C0 bloquea, no guarda nada más.
5. Si no bloquea: guarda como hallazgo cada movimiento con `estado_categoria != AUTO` (`WIILOG_MOVIMIENTO_REVISAR`),
   y cada orden de FF y flete con severidad distinta de `informativo`.
6. Responde `bloqueado`, ids de cargas, hallazgos creados y `resumen`. **El resumen y el C0 no se guardan.**
7. `GET /wallets/wiilog/hallazgos?empresa_id&periodo_id` con `conciliacion.ver`, filtra `codigo_regla LIKE 'WIILOG_%'`.

**Hallazgos del núcleo** (`app/core/hallazgos/`): columnas `critico` (bool), `resuelto`, `estado`
(`detectado → en_gestion → escalado → resuelto → cerrado`), `codigo_regla`, `descripcion`, `evidencia` (JSONB).
Endpoints: listar, detalle con mensajes, `escalar` (conciliador, pregunta obligatoria) y `responder`
(coordinador, solo si está `escalado`). El tipo de mensaje `NOTA` existe en la tabla pero **ninguna función lo usa**.

**Pantalla de Cartera** (`app/web/`): una sola página. `app.js` pide `/auth/me` (usuario, permisos, empresas),
llena el selector de empresa del encabezado, muestra u oculta los módulos del menú según permisos
(`navCartera.hidden = !permisos["cartera.ver"]`), y cambia de vista con `mostrarModulo()`. Todas las llamadas pasan
por `api()` (cookie de sesión; 401 → login). Estilo: `section.panel` + `panel-heading`, `status ok|error`,
`form-grid`, tablas simples, `formatearDecimal()` para montos en texto decimal. En el menú, "Wallets · Pronto" está
desactivado.

---

## 2. Conexión de Tiendas y Pagos (backend)

### 2.1 Endpoints

Carpeta `app/motores/conciliacion_wallets/plataforma/` (Fase 2): `api.py` (router `/wallets`), `integracion.py`
(base de datos, igual que `wiilog/integracion.py`) y `hallazgos.py` (Python puro: qué resultado se vuelve hallazgo).
`tiendas/` y `pagos/` siguen siendo Python puro, como piden sus CLAUDE.md.

| Endpoint | Permiso | Form / query |
|---|---|---|
| `POST /wallets/tiendas/conciliar` | `conciliacion.ejecutar` (empresa del form) | `empresa_id`, `periodo_id`, `tienda` (usuario_email), `fuente_wallet_id`, `fuente_ordenes_id`, `wallet`, `ordenes`, `corte_ordenes` opcional |
| `GET /wallets/tiendas/hallazgos` | `conciliacion.ver` (empresa del query) | `empresa_id`, `periodo_id`, `tienda` opcional |
| `POST /wallets/pagos/conciliar` | `conciliacion.ejecutar` | `empresa_id`, `periodo_id`, `wallet_pagos` (usuario_email), `fuente_wallet_id`, `wallet` |
| `GET /wallets/pagos/hallazgos` | `conciliacion.ver` | `empresa_id`, `periodo_id`, `wallet_pagos` opcional |
| `GET /wallets/catalogo` | `conciliacion.ver` | `empresa_id` → tiendas y wallets de pagos de **esa** empresa (de los JSON) |

Comportamiento, igual que Wiilog:

- Período de la empresa y abierto; si no, 409 con "Reábrelo antes de ejecutar la conciliación".
- La tienda o wallet elegida debe existir en el JSON **y su `empresa` debe coincidir con el nombre de la empresa
  elegida**. Si no: 422 "Esta tienda es de ORIGEN VITAL. Cambia la empresa en el encabezado." (no se infiere nada).
- Cargas con hash por archivo (`registrar_carga`); duplicado → 409 con el mismo mensaje de Wiilog.
- `corte_ordenes`: si no viene, se lee del nombre del archivo (`_AAAAMMDD_HHMMSS`, como indica §2 de la spec);
  si tampoco, el motor usa el fin del día de `FECHA DE REPORTE`. La respuesta dice cuál se usó.
- Tarifas de FF: de `parametros_wallet_wiilog.json` (única fuente), como hace la prueba de regresión.
- Respuesta: `bloqueado`, `c0` (el `detalle` del chequeo `C0_SALDO` y la advertencia de cobertura), ids de cargas,
  `hallazgos_creados`, `resumen` (el que ya arma el motor) y `corte_ordenes_usado`.

### 2.2 Qué se vuelve hallazgo

Regla única y sin inventar: **es hallazgo lo que el motor marca con gravedad distinta de `OK`** (`reglas.GRAVEDAD`
y la columna `gravedad` de cada resultado). La gravedad se guarda en `evidencia.gravedad`
(`CRITICO`/`MEDIO`/`INFORMATIVO`/`REVISAR`) y `critico = gravedad == "CRITICO"`, para que la política de cierre
siga funcionando igual.

| Regla | Es hallazgo | No es hallazgo |
|---|---|---|
| C0 | `C0_SALDO` BLOQUEADO (CRÍTICO; no se guarda nada más) · `C0_COBERTURA` ADVERTENCIA (INFORMATIVO) | EN_ORDEN |
| T1 Ganancia | SIN_PAGO, DIFERENCIA_VALOR (CRÍTICO) · PAGO_SIN_ENTREGA (MEDIO) · DUPLICADA (INFORMATIVO) | PAGADA, PAGADA_SIN_VALIDAR, EN_VENTANA, REVERSADA, NO_APLICA, PAGO_POSTERIOR_AL_REPORTE |
| T2 Sin recaudo | SIN_REEMBOLSO, REEMBOLSO_PARCIAL (CRÍTICO) · COBRO_DUPLICADO, DIFERENCIA_COBRO (MEDIO) · SIN_COBRO, REEMBOLSO_NO_ESPERADO (INFORMATIVO) | COBRO_CORRECTO, REEMBOLSADO, NO_APLICA |
| T3 Devolución | DUPLICADO, DIFERENCIA_TARIFA, COBRO_MAYOR_AL_FLETE (MEDIO) · SIN_COBRO, COBRO_ANTICIPADO (INFORMATIVO) | COBRADO, COBRADO_SIN_TARIFA, EN_VENTANA |
| T4 Fulfillment | DUPLICADO, DIFERENCIA_TARIFA, COBRO_NO_CORRESPONDE (MEDIO) · SIN_COBRO (INFORMATIVO) | COBRADO, COBRADO_SIN_TARIFA, REVERSADO, EN_VENTANA, NO_APLICA, COBRO_POSTERIOR_AL_REPORTE |
| Fuera del reporte | ORDEN_DE_OTRA_TIENDA, NO_ENCONTRADA (MEDIO, uno por movimiento) · ORDEN_ANTERIOR_AL_REPORTE (INFORMATIVO, **uno solo por carga de wallet**) | ORDEN_POSTERIOR_AL_REPORTE (gravedad OK en el motor) |
| Movimientos | `requiere_revision` (REVISAR, ver §3) | el resto |

Decisiones del 30-sep (Juan Felipe):

- `PAGADA_SIN_VALIDAR` y `COBRADO_SIN_TARIFA` **no** son hallazgo: se ven en el resumen, no en la bandeja.
- `REEMBOLSO_NO_ESPERADO` **sí** es hallazgo INFORMATIVO: se cambia en `tiendas/reglas.py` (`GRAVEDAD`), con prueba.
- `ORDEN_POSTERIOR_AL_REPORTE` **no** es hallazgo: se corrige en el motor (`fuera_del_reporte`, gravedad `OK`), con
  prueba. La integración no excluye nada por nombre; solo mira la gravedad.
- `ORDEN_ANTERIOR_AL_REPORTE`: en septiembre son miles de movimientos. **No** se guarda uno por movimiento: se guarda
  **un solo hallazgo INFORMATIVO por carga de wallet** (`TIENDA_FUERA_ORDEN_ANTERIOR_AL_REPORTE`), con el conteo y el
  neto por concepto en la evidencia y el texto "N movimientos de órdenes anteriores al reporte: carga el reporte de
  órdenes del mes anterior".

Código de regla: `TIENDA_T1_SIN_PAGO`, `TIENDA_T3_DIFERENCIA_TARIFA`, `TIENDA_FUERA_ORDEN_DE_OTRA_TIENDA`,
`TIENDA_C0_SALDO`, `PAGOS_C0_SALDO`, etc. Evidencia siempre con `wallet` (usuario_email), `tipo_wallet`, `gravedad`,
`carga_wallet_id`, `orden_id` o `mov_id`, montos en texto decimal (`"34998.00"`) y el estado de la regla.

Volumen con los archivos de septiembre (regresión en `tests/wallet_tiendas/test_regresion_tiendas_septiembre.py`):

| Wallet | CRÍTICO | MEDIO | INFORMATIVO | REVISAR | Total |
|---|---:|---:|---:|---:|---:|
| Menpros | 1 | 19 | 7 | 15 | 42 |
| Proveeduría ASIATI | 0 | 37 | 1 | 32 | 70 |

REVISAR subió el 6-oct (Menpros 10 → 15, Proveeduría 10 → 32): los retiros a banco quedan sin unidad de negocio y
los categoriza el conciliador (ver §3). Las cifras de la conciliación no cambian.

Sin agrupar habrían sido ~4.800 movimientos de órdenes anteriores al reporte y 289 de órdenes no encontradas.
NO_ENCONTRADA separa en su evidencia `reemplazadas` (Menpros 64, Proveeduría 0) y `otros` (116 y 109).

Wiilog: sus hallazgos ya existentes no traen `gravedad`. Se agrega `evidencia.gravedad` a los que se creen desde
ahora (crítico → CRITICO, severidad medio → MEDIO, movimiento → REVISAR, C0 advertencia → INFORMATIVO). No cambia
qué es hallazgo ni la severidad; solo la escribe. Para los viejos, la pantalla deduce CRITICO/MEDIO de `critico`.

### 2.3 Lo que queda fuera de estos endpoints

- **Cruce entre wallets** (`catalogo.cruzar_entre_wallets`, FF Proveeduría ↔ Wiilog): necesita varias wallets en la
  misma ejecución. Los endpoints concilian una wallet a la vez. Se propone después, cuando exista la entidad de
  ejecución del PR A.
- **Categorizar movimientos:** ya no espera la tabla de movimientos. Se guarda en `evidencia.categorizacion` del
  hallazgo REVISAR (ver §3 y `docs/nucleo/DIMENSIONES.md`).

---

## 3. Movimientos que requieren revisión

**Categorización manual (decisión 6-oct-2026, Juan Felipe Parra).** Todo movimiento `SIN_CONCEPTO` o con
`requiere_revision` lo categoriza el auxiliar de conciliación a mano, con las 7 dimensiones: ingreso/egreso, unidad de
negocio, categoría, empresa, tercero, modalidad y fijo/variable. Aplica a Wiilog, Tiendas y Pagos.

- El motor propone ingreso/egreso, unidad y categoría desde el catálogo común (`catalogo_conceptos_wallets.json`).
- El auxiliar solo elige de listas cerradas que administra el coordinador financiero. El único texto libre es el
  tercero (precargado desde el texto de Dropi). La empresa es la de la wallet y no se edita; la modalidad es WALLET.
- La observación es obligatoria. Si ninguna categoría sirve, el auxiliar escala al coordinador.
- Un texto de Dropi que el catálogo no reconoce (`SIN_CONCEPTO`) llega a revisión sin propuesta y marcado
  "Texto nuevo de Dropi" (`evidencia.texto_nuevo`).
- La categorización no se pierde al volver a conciliar la misma wallet y período (lo garantiza la clave estable
  de hallazgos del núcleo; ver `docs/decisiones/0008-categorizacion-manual-wallets.md`).

**En la pantalla.** Las filas REVISAR muestran fecha y número del movimiento, entrada o salida, monto, texto de Dropi,
tercero y la propuesta del motor, o la categoría elegida si ya se categorizó; un texto nuevo de Dropi lleva la marca
"TEXTO NUEVO DE DROPI". El detalle trae el formulario de las 7 dimensiones precargado (propuesta o categorización
previa): ingreso/egreso, unidad, categoría y fijo/variable como listas cerradas; empresa (la de la wallet) y modalidad
WALLET visibles y no editables; tercero editable; observación obligatoria; botones "Guardar" (queda en gestión),
"Guardar y resolver" y "Escalar".

La evidencia de cada movimiento por revisar trae, además, el texto de Dropi (`texto_dropi`), entrada o salida
(`entrada_salida`), el monto en pesos (`monto`) y la propuesta del motor (`ingreso_egreso`, `unidad_negocio`,
`categoria`), igual en Wiilog, Tiendas y Pagos.

Propuesta: cada movimiento con `requiere_revision` se guarda como hallazgo con `codigo_regla`
`TIENDA_MOVIMIENTO_REVISAR` o `PAGOS_MOVIMIENTO_REVISAR`, `evidencia.tipo = "REVISAR_MOVIMIENTO"`, gravedad REVISAR,
`critico = false`, y en la evidencia: `mov_id`, fecha, concepto, ingreso/egreso, categoría propuesta, tercero,
`tipo_tercero` (WALLET_PROPIA / CUENTA_DESTINO_GRUPO / EXTERNO), monto y la observación sugerida del motor.

**Encaja:** Wiilog ya hace exactamente esto (`WIILOG_MOVIMIENTO_REVISAR`). Se sigue el mismo patrón.

**Choca en un punto:** el núcleo no tiene cómo dejar la observación del conciliador. Hoy:

- `responder` solo lo puede usar el **coordinador** y solo si el hallazgo está `escalado`.
- `escalar` es una pregunta al coordinador, no una observación.
- El permiso `hallazgos.gestionar` ("asignar, justificar, marcar resuelto") existe en la matriz, pero **no hay
  endpoint** que lo use. El tipo de mensaje `NOTA` existe pero no se usa.

Por eso se necesita un **PR pequeño en `app/core`** (de Adrian, te lo muestro antes):

```
POST /api/v1/hallazgos/{id}/observar   permiso hallazgos.gestionar   {observacion, resolver: bool}
```

- Guarda un mensaje `NOTA` con la observación (obligatoria, mismo error que `escalar`).
- Estado: `detectado → en_gestion`; con `resolver=true`, `detectado|en_gestion → resuelto` y `resuelto = true`.
  Un hallazgo `escalado` no se puede resolver por aquí (lo decide el coordinador).
- Período cerrado → 409. Auditoría en la misma transacción (`hallazgo.observar`).
- Pruebas por rol (conciliador y coordinador sí en sus empresas; TI no; empresa no asignada → 404).

Sin ese PR, la pantalla solo podría escalar; no podría dejar la observación ni marcar resuelto.

---

## 4. La pantalla

Nueva vista `vista-wallets` en `index.html`, con los mismos componentes de Cartera. La empresa se toma del selector
del encabezado (como Cartera). Orden:

1. **Selector** (panel "Conciliar wallet"): período (lista de la empresa; los cerrados aparecen marcados
   "Cerrado" y no permiten conciliar), tipo de wallet (Wiilog marca blanca / Tienda / Pagos) y, para Tienda o Pagos,
   cuál (lista de `GET /wallets/catalogo` filtrada por la empresa; si la empresa no tiene ninguna, el mensaje lo dice).
   Fuente de la wallet y de las órdenes: lista de fuentes de la empresa (ver §6).
2. **Carga de archivos:** wallet siempre; órdenes solo para Wiilog y Tienda. Para Tienda, campo opcional
   "Hora de descarga del reporte" (se precarga si el nombre del archivo la trae). Botón **Conciliar**. Mientras
   corre, el botón queda deshabilitado con "Conciliando…" (Proveeduría tiene 17.545 movimientos).
3. **Resultado C0:** saldo inicial, entradas, salidas, saldo final y una etiqueta **"CUADRA"** o **"NO CUADRA"**.
   Si no cuadra: "El saldo no cuadra en N puntos. El archivo puede estar incompleto: descárgalo de nuevo de Dropi y
   vuelve a conciliar." y **no se muestran** resumen ni hallazgos. La advertencia de cobertura se muestra aparte.
4. **Resumen:** como la hoja Resumen del Excel de septiembre: una tabla por regla (T1, T2, T3, T4, fuera del
   reporte, movimientos) con Estado · Órdenes · Monto en juego · Qué significa. "Qué significa" se toma de la spec,
   no se redacta nuevo.
5. **Bandeja de hallazgos:** filtros por gravedad (Crítico / Medio / Informativo / Revisar) y por estado
   (detectado / en gestión / escalado / resuelto). Cada fila: gravedad, orden o movimiento, descripción, monto,
   estado y acciones según rol: **Observar** (texto; opcional "marcar resuelto"), **Escalar** (pregunta),
   **Responder** (solo coordinador, si está escalado). Detalle con el hilo de mensajes.
6. **Estados con palabra:** cada gravedad y estado se escribe en texto ("CRÍTICO", "EN GESTIÓN"); el color es
   adicional. Se prueba con impresión en blanco y negro (`@media print`).

Limitación honesta: como el C0 y el resumen no se guardan (PR B de Adrian), **solo se ven justo después de
conciliar**. Si se recarga la página se ve la bandeja, no el resumen. Mientras tanto se guardan en
`sessionStorage` del navegador con un aviso "Resumen de la última conciliación de esta sesión".

---

## 5. Qué ve y qué puede hacer cada rol

| | Conciliador | Coordinador financiero | Superadmin | TI |
|---|---|---|---|---|
| Ver menú Wallets (`conciliacion.ver`) | Sus empresas | Sus empresas | Todas | Todas (lectura) |
| Subir y conciliar (`conciliacion.ejecutar`) | Sí | No (no ve el panel de carga) | Sí | No |
| Observar / marcar resuelto (`hallazgos.gestionar`) | Sí | Sí | Sí | No |
| Escalar (`hallazgos.escalar`) | Sí | No | Sí | No |
| Responder escalado (`hallazgos.responder_escalado`) | No | Sí | Sí | No |

La pantalla solo **presenta** según `/auth/me`; el backend valida siempre. Empresa no asignada → 404.

---

## 6. Datos base que necesita la pantalla

| Dato | ¿Existe? | Quién lo crea y cómo |
|---|---|---|
| Empresas WIILOG, ASIATI, TIENDAS ASIATI, ORIGEN VITAL | **No hay endpoint ni script.** Local: solo "ASIATI Demo" del bootstrap. `ROLES_Y_PERMISOS.md §2` nombra WIILOG, CHIN CHIN, ASIATI COMERCIAL | PR aparte en `app/core` (después del de tiendas y pagos): comando que crea empresas, períodos y fuentes desde un archivo; el archivo con los nombres reales va fuera de git y en el repo solo un ejemplo. Nombres decididos el 30-sep: **WIILOG, ASIATI, TIENDAS ASIATI, ORIGEN VITAL**, idénticos al campo `empresa` de los JSON (`parametros_wallet_pagos.json` ya dice `ASIATI`). |
| Períodos (sept-2026 abierto por empresa) | No hay endpoint para crear ni listar períodos | El mismo PR de núcleo: crear con el comando y listar con `GET /periodos?empresa_id` (lectura) |
| Fuentes por wallet | `fuentes` solo tiene `empresa_id` y `nombre`; no hay endpoint | El mismo PR de núcleo: crear con el comando (una fuente por archivo y empresa) y listar con `GET /fuentes?empresa_id`. La pantalla deja **elegir** la fuente; no se deduce del nombre |
| Usuarios con empresas asignadas | Sí (`PUT /usuarios/{id}/empresas`) | Tú como superadmin, desde la API o la pantalla de usuarios |

Para probar en local, en la Fase 3 creo estos datos con un script **solo local, fuera del repo** (scratchpad),
con nombres de ejemplo y sin datos reales. No se sube.

---

## 7. Decisiones sobre lo que no cuadraba

1. **Hash de cargas único por empresa.** Menpros y Recompra Menpros (ambas ORIGEN VITAL) usan el mismo reporte de
   órdenes. Decisión 30-sep: el motor **reutiliza la carga de órdenes** si el mismo hash ya existe en la misma
   empresa **y el mismo período**. En otro período sigue siendo 409. El núcleo no cambia.
2. **Reconciliar con una wallet nueva** ya no crea otra tanda (decisión 0008, 6-oct): cada hallazgo tiene clave
   estable (wallet + regla + `mov_id` u `orden_id`) y se actualiza conservando estado, observaciones, escalamiento y
   categorización. Lo que ya no aparece queda "resuelto por el sistema". La bandeja muestra los **vigentes**; el
   historial (casilla "Mostrar historial") incluye lo resuelto por el sistema y los hallazgos anteriores a la clave.
   Wiilog reutiliza órdenes y wallet por empresa, período, fuente y hash (decisión 6-oct, PR #126).
   El 409 de conciliación repetida corresponde a la **pareja** de cargas ya ejecutada, no a la existencia
   individual de ambos archivos. Una combinación nueva de archivos conocidos sí se concilia.
   Desde la migración `0019_wiilog_reconciliations`, cada ejecución guarda su pareja, usuario y fecha, aun sin
   hallazgos o con C0 bloqueado. La bandeja selecciona por ejecución, no por el mayor ID de wallet; por eso
   reutilizar una carga antigua no oculta los hallazgos vigentes y un resultado sin hallazgos deja la bandeja vacía.
   Las ejecuciones del mismo período se serializan y se confirman junto con cargas y hallazgos.
   No se reconstruyen parejas históricas: antes de esta migración no se guardaban. Los períodos sin ejecución
   registrada conservan la consulta anterior hasta la primera reconciliación, que registra la pareja incluso
   si ambos archivos ya existían. Desde entonces repetir esa pareja devuelve 409.
   Tiendas conserva su criterio anterior: reutiliza órdenes, pero rechaza una wallet repetida.
3. **C0 y resumen no persistidos:** se guardan en `sessionStorage` con el aviso "Resumen de la última conciliación de
   esta sesión", hasta el PR B.
4. **Cruce entre wallets:** después del PR A de Adrian.
5. La auditoría del 29-sep solo está en la rama `docs/core-wallets-architecture-audit`.
6. `main` despliega al Lightsail de desarrollo (no a producción) desde el 30-sep. No hacemos merge.

Orden de PR: primero el del núcleo (`POST /hallazgos/{id}/observar`, aprobado 30-sep), después tiendas y pagos,
después la pantalla.

## 8. Pruebas

Backend (Fase 2):

- `tests/wallet_tiendas/test_integracion_tiendas.py` y `tests/wallet_pagos/test_integracion_pagos.py`, con
  DataFrames sintéticos: qué estado se vuelve hallazgo y cuál no (una prueba por fila de la tabla §2.2), gravedad
  y `critico`, montos en texto decimal, C0 bloqueado no guarda nada más, tienda de otra empresa → error,
  `corte_ordenes` desde el nombre del archivo.
- `tests/test_core_wallet_tiendas_api.py` y `..._pagos_api.py` (integración con Postgres): permisos por rol
  (conciliador sí / coordinador no ejecuta / TI no ejecuta / empresa no asignada 404), período cerrado 409,
  archivo duplicado 409, reutilización de órdenes en la misma empresa y período.
- Regresión con fixtures reales (`@pytest.mark.fixtures_reales`): conteos de hallazgos de septiembre coinciden con
  §6 y §7 de la spec (1 CRÍTICO en Menpros, 12 DUPLICADO en Proveeduría, etc.).
- PR del núcleo: `tests/test_core_hallazgos_observar.py` (transiciones, texto obligatorio, auditoría, roles).

Frontend (Fase 3):

- `tests/test_web_wallets.py`: el HTML trae la vista y los paneles; el JS consume los endpoints nuevos; "Wallets"
  ya no está como "Pronto"; cada estado tiene texto.
- Local: `docker compose up`, datos base con el script local, subir los archivos de septiembre de `fixtures/`
  (Menpros, Proveeduría, Recompra, pagos@, Wiilog) y tomar capturas de cada paso con el navegador de la app.
  Las capturas no muestran filas reales en el PR: se tapan órdenes y correos o se usan solo las de resumen.

---

## 9. Cambios que tocan `app/core` o `app/web` (para Adrian)

`app/core` (PR aparte, pequeño, se muestra antes):

1. `app/core/hallazgos/escalamiento.py`: `transicion_observar()`.
2. `app/core/hallazgos/casos.py`: `observar_hallazgo()` (NOTA + auditoría).
3. `app/core/hallazgos/api.py`: `POST /hallazgos/{id}/observar`.
4. `docs/nucleo/ROLES_Y_PERMISOS.md §8`: agregar el endpoint.
5. Prueba nueva. Sin migración (la tabla y el tipo `NOTA` ya existen).

Segundo PR de núcleo (después de tiendas y pagos): comando de datos base (empresas, períodos, fuentes) con archivo de
ejemplo en el repo y el real fuera de git, más `GET /periodos?empresa_id` y `GET /fuentes?empresa_id` (lectura).

`app/main.py`: registrar los routers de tiendas y pagos (dos líneas, como Wiilog).

`app/web` (solo Wallets):

1. `index.html`: botón "Wallets" activo (sale de "Próximamente") y `<div id="vista-wallets">`.
2. `app.js`: `mostrarModulo("wallets")`, permisos del menú y funciones de la vista. Se agrega en un bloque propio
   al final; no se modifica lo de Cartera ni Compras.
3. `styles.css`: etiquetas de gravedad y estado, y `@media print`.
4. `tests/test_web_shell.py` no cambia (sigue buscando "Wallets").

Sin migraciones nuevas en ningún PR.
