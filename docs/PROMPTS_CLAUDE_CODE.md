# Arranque con Claude Code · roles, parámetros y wallet Wiilog

Cinco sesiones, en este orden. Cada una es una rama y un PR. Pega el texto del recuadro como primer mensaje en Claude Code, abierto en la raíz del repo `Financial-System-Asiati`.

Antes de la primera sesión:

1. `git switch main && git pull && git switch -c feat/wiilog-wallet-reference`
2. Copia el contenido de este paquete a la raíz del repo (respeta las carpetas).
3. Copia los dos archivos reales de septiembre a `fixtures/wallet_wiilog/2026-09/` con estos nombres exactos:
   `ordenes_sept_20260928_144134.xlsx` y `historyWallet_20260928_142641.xlsx`.
4. Confirma que `fixtures/` está en `.gitignore`. **Esos archivos no se suben nunca.**

Si ya se aprobó mover el código a `backend/` (decisión 0002), esa mudanza va antes que todo, en su propio PR.

---

## Sesión 1 · Motor de referencia de la wallet Wiilog (Juan Felipe)

```
Lee CLAUDE.md, docs/motores/conciliacion_wallets/WALLET_WIILOG.md y
docs/motores/conciliacion_wallets/parametros_wallet_wiilog.json.

Acabo de copiar al repo el paquete app/motores/conciliacion_wallets/wiilog/ y sus
pruebas en tests/wallet_wiilog/. Es Python puro, sin base de datos, y ya reproduce
septiembre.

Tu tarea:
1. Integra el paquete a la estructura del repo sin cambiar la lógica de las reglas.
   Ajusta imports, rutas y el pyproject (marcador pytest fixtures_reales).
2. Corre pytest tests/wallet_wiilog. Los 23 sintéticos deben pasar. Los 7 de
   regresión deben pasar con los archivos de fixtures/ y saltarse si no están.
3. Agrega el job de CI que corre los sintéticos (los de regresión se saltan en CI).
4. No toques app/core. No crees tablas. No cambies ninguna cifra de la línea base.
5. Verifica que ningún archivo de fixtures/ quede en el diff y usa /pr.
```

## Sesión 2 · Usuarios, roles y empresas asignadas (núcleo · revisa Adrian)

```
Lee CLAUDE.md, docs/SPEC_NUCLEO.md y docs/nucleo/ROLES_Y_PERMISOS.md.
ROLES_Y_PERMISOS reemplaza la tabla de roles de SPEC_NUCLEO §7.

Construye en el núcleo, con test primero:
1. Tablas usuarios, usuario_empresas, ingresos, hallazgo_mensajes y auditoria (si no
   existe), con migraciones Alembic. Rol como texto con CHECK de los cinco valores.
2. Login con Argon2, JWT en cookie HttpOnly/Secure/SameSite=Strict, límite de
   intentos, cambio de contraseña obligatorio en el primer ingreso. Cada intento de
   login escribe en ingresos.
3. La matriz de permisos en código (§3) y una dependencia de FastAPI
   requiere(permiso, empresa_de=...) que aplique el alcance TODAS o ASIGNADAS.
   Recurso de empresa no asignada responde 404.
4. Endpoints de la §8 para usuarios, empresas asignadas, supervisión y escalar/
   responder hallazgos.
5. Un comando para crear el primer SUPERADMIN desde la terminal (sin endpoint público).
6. Las pruebas obligatorias de la §7: cada endpoint contra cada rol.

No implementes pantallas en esta sesión. Mensajes de error en castellano y diciendo
qué hacer. Usa /pr al terminar.
```

## Sesión 3 · Parámetros versionados y catálogo de conceptos (núcleo · revisa Adrian)

```
Lee docs/SPEC_NUCLEO.md §3 (parametros_versiones, reglas_categorizacion) y
docs/motores/conciliacion_wallets/parametros_wallet_wiilog.json.

1. Tabla parametros_versiones con migración. Los parámetros nunca se sobrescriben:
   PUT crea una versión nueva. Solo SUPERADMIN edita (permiso parametros.editar).
2. Carga el JSON de la wallet Wiilog como versión 1 de la fuente "Wallet Wiilog"
   de la empresa WIILOG, con una migración de datos.
3. Tabla reglas_categorizacion. Siembra desde conceptos_wallet del JSON y desde
   CATEGORIA_POR_CONCEPTO en app/motores/conciliacion_wallets/wiilog/movimientos.py:
   patrón, tipo de match (EMPIEZA_CON / CONTIENE), prioridad = orden en la lista,
   categoría por defecto, requiere_revision y requiere_observacion.
4. Endpoints GET /parametros, PUT /parametros, GET /reglas con permisos.
5. Una prueba que compruebe que un cierre guarda la versión de parámetros que usó.
Usa /pr al terminar.
```

## Sesión 4 · El enchufe: cargar, ejecutar y guardar resultados

```
Lee docs/motores/conciliacion_wallets/WALLET_WIILOG.md y el contrato de motor en
app/core/motor.py.

Conecta el motor wiilog al núcleo:
1. Carga de dos archivos (órdenes y wallet) por período y fuente, con hash para no
   cargar dos veces el mismo archivo. Guarda el crudo.
2. validar() corre C0. Si C0 queda BLOQUEADO, no se puede ejecutar y el mensaje
   dice qué hacer.
3. ejecutar(periodo, fuente, params) llama a conciliar_wallet_wiilog y guarda:
   - los movimientos de la wallet con concepto, categoría, estado, tercero, cruce y
     un campo observacion editable;
   - un resultado por orden y regla (FF, FLETE) con su estado y monto en juego;
   - un hallazgo por cada resultado crítico o medio.
   Montos en NUMERIC(18,2) desde los centavos enteros del motor.
4. PATCH de un movimiento: categoría y observación (permiso movimientos.categorizar).
   Un movimiento con requiere_observacion no puede quedar sin observación al cerrar
   el período: el cierre lo rechaza y lista cuáles faltan.
5. Prueba de integración: con los archivos de fixtures, lo guardado en base
   reproduce la línea base de WALLET_WIILOG.md §7.
Usa /pr al terminar.
```

## Sesión 5 · Pantallas

```
Lee docs/nucleo/ROLES_Y_PERMISOS.md §5 y §7 y el sistema visual de SPEC_NUCLEO §11.

Construye en el frontend, usando /auth/me para mostrar solo lo permitido:
1. Login y cambio de contraseña.
2. Layout: barra lateral, selector con solo las empresas asignadas, período.
3. Wallet Wiilog:
   a. Carga de los dos archivos y resultado de C0 chequeo por chequeo.
   b. Resumen: FF y flete por estado, pesos primero y conteos después.
   c. Hallazgos: tabla filtrable por estado, bodega y días; acciones justificar,
      resolver y escalar con pregunta.
   d. Movimientos por revisar: categoría editable y campo Observación.
4. Supervisión (coordinador): estado de conciliaciones, últimos ingresos, acciones
   por usuario, casos escalados.
5. Usuarios (superadmin): crear, asignar rol y empresas, desactivar, restablecer.
Cada estado lleva su palabra además del color. Usa /pr al terminar.
```
