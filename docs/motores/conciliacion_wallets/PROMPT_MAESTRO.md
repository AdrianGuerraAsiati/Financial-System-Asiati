# PROMPT MAESTRO V4 — MOTOR `conciliacion_wallets`

> Para pegar en Claude Code, abierto en la carpeta del proyecto.
> Versión 4 · septiembre 2026 · reemplaza a la V3.
>
> **Qué cambió de la V3 a la V4:** el proyecto dejó de ser una aplicación suelta y pasó a ser un motor dentro de una plataforma. El núcleo lo construye y lo mantiene otra persona. Este prompt construye **únicamente el motor de conciliación de wallets**, enchufado a ese núcleo.

---

## CÓMO USAR ESTE DOCUMENTO

1. Completá la sección **§0 · BLOQUEANTES**. Son cuatro cosas y salen de una sola sesión de parámetros.
2. Poné en `fixtures/` los archivos de referencia y guardá este documento como `PROMPT_MAESTRO.md` en la raíz del motor.
3. **Adjuntá `SPEC_NUCLEO.md`** junto a este prompt. Es el contrato contra el que se enchufa todo lo que construyas.
4. Abrí Claude Code ahí y escribí: *"Lee PROMPT_MAESTRO.md y SPEC_NUCLEO.md. Ejecuta la FASE 0 y para cuando termines."*
5. Avanzá fase por fase. No dejes que salte fases.

---

## §0 · BLOQUEANTES — COMPLETAR ANTES DE ARRANCAR

| # | Qué falta | Estado |
|---|---|---|
| 1 | **Catálogo de conceptos de las tres wallets** — el texto exacto que trae cada exportación de Dropi | ⬜ |
| 2 | **Regla de comisión de flete** (wallet Tiendas): ¿porcentaje, valor fijo o tabla por transportadora? | ⬜ |
| 3 | **Cómo Wiilog cobra el fulfillment por guía** — la regla de su conciliación | ✅ Resuelto: ver [`WALLET_WIILOG.md`](WALLET_WIILOG.md) |
| 4 | Archivos en `fixtures/`: órdenes de julio, las exportaciones de las tres wallets, y el resultado esperado de la corrida manual | ⬜ |

Sin el punto 2 el motor puede construirse igual, pero la regla C3 sale con ruido y nadie le va a creer al resto del tablero.

---

## §1 · ROL Y ENCARGO

Actuá como **desarrollador senior de Python con criterio de auditoría contable**.

Vas a construir el motor `conciliacion_wallets` de la Plataforma Financiera de ASIATI: el módulo que cruza los movimientos de las billeteras de Dropi contra las órdenes y las guías que los respaldan, y produce los hallazgos que alguien tiene que resolver.

Quiero código funcional y probado, no documentación ni pseudocódigo.

**Prioridades, en este orden:**

1. Corrección de las reglas de negocio
2. Integridad de los datos contables
3. Trazabilidad: por qué el motor decidió lo que decidió
4. Mantenibilidad
5. Rendimiento
6. Apariencia de las pantallas

---

## §2 · LO QUE YA EXISTE Y NO DEBÉS CONSTRUIR

**Esto es lo más importante de todo el documento.** El núcleo de la plataforma lo construye y lo mantiene otra persona. Si lo reconstruís, vas a crear un sistema paralelo al que el equipo está montando.

**No construyas, no toques, no dupliques:**

```
identidad, roles y permisos          empresas y unidades de negocio
períodos, cierres y congelado        cargas de archivo (hash, idempotencia)
la tabla de movimientos              el categorizador de las 7 dimensiones
el catálogo de reglas de categorización
hallazgos y su ciclo de vida         parámetros versionados
bitácora de auditoría                export a Excel
monorepo, Docker, Postgres, Alembic, Nginx, despliegue, CI
```

Todo eso ya está especificado en `SPEC_NUCLEO.md` y lo consume tu motor a través del contrato.

**Un malentendido que hay que evitar:** la categorización de movimientos en las siete dimensiones del flujo de caja —ingreso/egreso, unidad de negocio, categoría, empresa, tercero, modalidad, fijo o variable— **es del núcleo, no de este motor**. La necesitan todos los dominios de la plataforma, no solo wallets. Tu motor recibe los movimientos ya categorizados y se ocupa de otra cosa: cruzarlos contra su soporte.

**Tu motor aporta solamente:**

- Qué fuentes consume y cómo las lee
- Contra qué soporte cruza cada wallet
- Las reglas C0 a C6 y los estados que producen
- Su esquema de parámetros
- Sus tablas propias de dominio (órdenes, emparejamientos)
- Sus pantallas de detalle

---

## §3 · EL CONTRATO DEL MOTOR

El núcleo espera esta forma. Está en `SPEC_NUCLEO.md §5`; si hay diferencia entre este resumen y esa spec, **manda la spec**.

```python
class ClaseMotor(str, Enum):
    CONCILIACION = "conciliacion"
    REPORTE      = "reporte"

class Motor(Protocol):
    slug: str                       # "conciliacion_wallets"
    nombre: str                     # "Conciliación de wallets"
    clase: ClaseMotor               # CONCILIACION
    fuentes_requeridas: list[str]

    def esquema_parametros(self) -> dict: ...
    def validar(self, carga, params) -> ResultadoValidacion: ...
    def ejecutar(self, periodo, fuente, params) -> list[Resultado]: ...
```

En el frontend, el motor registra sus rutas y componentes en `src/registro.ts`.

**Dos reglas de diseño que no se negocian:**

**1. El motor es la unidad de código; la empresa es un dato.** Vas a construir UN solo `conciliacion_wallets` que sirve a las tres wallets mediante tres juegos de parámetros. Nunca tres carpetas, nunca tres copias. En la interfaz sí se navega por empresa, pero eso es una ruta y una fila de configuración.

**2. El motor no sabe de dónde vinieron los datos.** Recibe filas ya normalizadas por el núcleo. Si mañana entran por API de Dropi en vez de por Excel, el motor no se entera.

**Estructura de carpetas:**

```
backend/app/motores/conciliacion_wallets/
├── __init__.py          registra el motor
├── parser.py            lee las exportaciones de Dropi
├── matcher.py           la cascada de emparejamiento
├── rules/
│   ├── c0.py … c6.py
│   └── __init__.py
├── models.py            las tablas propias del motor
├── schemas.py
└── tests/

frontend/src/motores/conciliacion-wallets/
├── rutas.tsx
├── pantallas/
└── componentes/
```

**El paquete de reglas es Python puro.** Sin FastAPI, sin SQLAlchemy, sin base de datos: recibe DataFrames y un dict de parámetros, devuelve resultados. Se prueba sin levantar nada. Esa separación es lo que permite construir y probar el motor antes de que el núcleo esté terminado.

---

## §4 · LAS TRES WALLETS

Una sola es la que cruza contra órdenes. Las otras dos son distintas y hay que respetarlo.

| Wallet | Naturaleza | Soporte del cruce | Qué hace el motor |
|---|---|---|---|
| **Tiendas** | Dropshipping | Órdenes de Dropi | Reglas C0 a C6 completas |
| **Wiilog** | Recaudadora | Guías: recauda el servicio de fulfillment por guía | Juego propio de reglas, por definir en §0.3 |
| **ASIATI** | Recaudadora | Ninguno — solo recibe transferencias de las otras wallets | **Nada.** Solo la categorización del núcleo |

**Consecuencia:** el motor debe poder declarar que una fuente no tiene reglas de cruce. Para la wallet de ASIATI, `ejecutar()` devuelve una lista vacía y eso es correcto, no un error.

**Una observación para dejar preparada, sin implementar todavía:** si Wiilog recauda el fulfillment que la wallet de Tiendas paga, esos dos movimientos son el mismo hecho visto desde dos lados. Y lo que sale de ambas termina en ASIATI. Dejá el modelo listo para una conciliación entre wallets —salida de una contra entrada de otra— pero **no la construyas en esta entrega**.

---

## §5 · LO QUE YA SABEMOS, CON DATOS REALES

Esta sección es la parte más valiosa del documento. No son supuestos: salieron de una corrida manual con pandas sobre los archivos de julio de 2026.

### Las cifras que el motor tiene que reproducir

```
Órdenes ENTREGADAS sin pago en wallet          1.555 · $97.292.151
  de las cuales, excluidas por SIN RECAUDO       628
Órdenes pagadas dos o tres veces                  28 · $1.826.231 de exceso
Salidas del wallet sin orden que las respalde     80 · $4.931.165
  de las cuales, de 2025 (fuera del rango)        79
  devolución pagada por error                      1  (orden 70754343 / guía 240049399139)
```

**Si el motor no reproduce estas cifras con los mismos archivos, el motor está mal, no los datos.** Escribí este test antes de escribir las reglas.

### Las seis correcciones obligatorias

Seis cosas estaban mal en el diseño original. **No las implementes como estaban.**

**1. El wallet paga ganancia, no valor de venta.** La versión anterior comparaba el pago contra `VALOR DE COMPRA EN PRODUCTOS`. Lo que entra al wallet es `GANANCIA TOTAL DE DROPSHIPPER` sumada por orden. Con la comparación anterior, C1 marcaría el 100 % de las órdenes como diferencia.

**2. Sin recaudo es una exclusión, no un hallazgo.** 628 de las 1.555 faltantes eran envíos sin recaudo. Van fuera del universo conciliable, declaradas en parámetros y contabilizadas aparte. Nunca aparecen en la bandeja.

**3. El pago llega con rezago.** Una orden entregada hace cinco días sin pago es normal, no un hallazgo. Parámetro `ventana_gracia_dias`, arranca en 15. Dentro de la ventana el estado es `EN_VENTANA`; pasada, `SIN_PAGO`.

**4. Agrupar por orden antes de cruzar.** La base trae una fila por línea de producto; el wallet, una entrada por orden. Si cruzás sin agrupar, los montos se multiplican por el número de líneas.

**5. La referencia del wallet es una pista, no una llave.** A veces trae el ID, a veces la guía, a veces texto libre. Cascada, guardando siempre con qué nivel emparejó:

```
nivel 1  referencia == orden_id                    → EXACTA
nivel 2  referencia == numero_guia                 → EXACTA
nivel 3  dígitos(referencia) contiene el orden_id  → PROBABLE
nivel 4  monto + fecha ±2d + dropshipper_id        → PROBABLE
nivel 5  sin match                                 → SIN_MATCH
```

Del nivel 3 en adelante pasa a revisión humana. **Nunca se cierra solo.**

**6. Validar el archivo antes de conciliar.** 79 de las 80 huérfanas eran de 2025, fuera del rango del archivo. Un archivo truncado produce una conciliación falsa que se ve perfectamente correcta. Eso es C0, y es un freno.

---

## §6 · LAS SIETE REGLAS

Cada regla recibe el cruce ya hecho y devuelve, por orden o por movimiento, un estado y un monto en juego.

### C0 — Integridad de la carga (FRENO)
```
a) Todas las columnas declaradas en parámetros están presentes
b) El rango de fechas de las órdenes cae dentro del período
c) El rango de fechas del wallet cubre el período completo, sin días faltantes
d) saldo_final == saldo_inicial + sum(ENTRADAS) - sum(SALIDAS)   [tolerancia: 1 peso]

(a), (c) o (d) fallan → BLOQUEADO. La conciliación NO se ejecuta.
(b) falla → ADVERTENCIA. Continúa con confirmación explícita.
```
El chequeo del hash duplicado lo hace el núcleo antes de llamarte; no lo dupliques.
El chequeo (d) es la forma más barata de detectar un export a medias. **No lo omitas.**

### C1 — Ganancia pagada
```
Universo: ESTATUS en estatus_pagables, excluyendo TIPO DE ENVIO en tipos_sin_recaudo.
  esperado = suma de ganancia de sus líneas
  pagado   = ENTRADAS de concepto pago_ganancia emparejadas
  dias     = fin de período - FECHA ENTREGADO

  pagado == 0 y dias <= ventana_gracia   → EN_VENTANA
  pagado == 0 y dias >  ventana_gracia   → SIN_PAGO           [crítico]
  |pagado - esperado| <= tolerancia      → PAGADA
  |pagado - esperado| >  tolerancia      → DIFERENCIA_VALOR   [hallazgo]
```

### C2 — Fulfillment cobrado
```
Universo: órdenes con guía generada, no canceladas ni rechazadas.
  Existe SALIDA de cobro_fulfillment emparejada  → COBRADO
  No existe                                      → NO_COBRADO  [hallazgo]
  Monto distinto del esperado (± tolerancia)     → DIFERENCIA_VALOR
```

### C3 — Flete y comisión
```
Universo: órdenes donde la regla de flete aplica (ver §0.2).
  Existe SALIDA de cobro_flete emparejada        → COBRADO
  No existe y la regla aplica                    → NO_COBRADO  [hallazgo]
  No aplica a esa transportadora o tipo de envío → NO_APLICA
```
La regla vive entera en `parametros.reglas_flete` y soporta las tres formas —porcentaje, valor fijo y tabla por transportadora— desde el primer día, aunque solo se use una.

### C4 — Devoluciones compensadas
```
Universo: ESTATUS en estatus_devolucion.
  Existe SALIDA de cobro_devolucion emparejada   → COMPENSADA
  No existe                                       → SIN_COBRO      [hallazgo]
  Existe además ENTRADA de pago_ganancia          → PAGO_INDEBIDO  [crítico]
```
`PAGO_INDEBIDO` es el caso de la orden 70754343: devuelta y pagada. Que el sistema lo detecte solo es una de las razones de existir del proyecto.

### C5 — Salidas justificadas
```
Universo: TODOS los movimientos del wallet del período.
  Emparejado a orden del período                  → JUSTIFICADA
  Emparejado a orden fuera del rango del archivo  → FUERA_DE_RANGO  [informativo]
  Sin match y concepto operativo                  → HUERFANA        [hallazgo]
  Sin match y concepto no operativo               → NO_APLICA
```
Los conceptos no operativos —recarga de tarjeta, transferencia entre wallets, retiro de saldo, mantenimiento de tarjeta, dispersión, impuesto del cuatro por mil— son movimiento de plata propia del dropshipper. **No los levantes como hallazgos.** La categorización de esos movimientos ya la hizo el núcleo.

### C6 — Valor y duplicados
```
Para cada orden con al menos un pago emparejado:
  Una sola ENTRADA de pago_ganancia               → EXACTA
  Dos o más ENTRADAS de pago_ganancia             → DUPLICADA   [crítico]
  |pagado - esperado| > tolerancia                → DIFERENCIA  [hallazgo]
```
Calculá y reportá el exceso pagado por orden y el total del período.

### Score
```
score = 100 * (1 - monto_en_hallazgos_criticos / monto_total_conciliable)
```
Redondeado a un decimal, por fuente. El núcleo lo guarda en `cierres_motor.score`.

---

## §7 · PARÁMETROS — UN JUEGO POR WALLET

Los parámetros los versiona y los guarda el núcleo. Tu motor solo declara el esquema y los consume.

```json
{
  "fuente_tipo": "WALLET_TIENDAS",

  "columnas_ordenes": {
    "orden_id": "ID",
    "guia": "NÚMERO GUIA",
    "estatus": "ESTATUS",
    "tipo_envio": "TIPO DE ENVIO",
    "ganancia": "GANANCIA TOTAL DE DROPSHIPPER",
    "valor_producto": "VALOR DE COMPRA EN PRODUCTOS",
    "precio_flete": "PRECIO FLETE",
    "fulfillment": "TOTAL FULFILLMENT",
    "transportadora": "TRANSPORTADORA",
    "dropshipper_id": "DROPSHIPPER ID",
    "fecha_guia": "FECHA GENERACION DE GUIA",
    "fecha_entrega": "FECHA ENTREGADO"
  },
  "columnas_wallet": {
    "fecha": "FECHA", "concepto": "CONCEPTO", "tipo": "TIPO",
    "valor": "VALOR", "referencia": "REFERENCIA", "saldo": "SALDO"
  },

  "estatus_pagables":   ["ENTREGADO"],
  "estatus_devolucion": ["DEVOLUCION", "DEVUELTA"],
  "estatus_excluir":    ["CANCELADO", "RECHAZADO"],
  "tipos_sin_recaudo":  ["SIN RECAUDO"],

  "conceptos_wallet": {
    "pago_ganancia":     ["ENTRADA POR GANANCIA EN LA ORDEN"],
    "cobro_fulfillment": ["SALIDA POR NUEVA ORDEN"],
    "cobro_flete":       ["SALIDA POR COBRO DE FLETE INICIAL"],
    "cobro_devolucion":  ["SALIDA DE COBRO DE DEVOLUCION POR ENTREGA NO EFECTIVA"]
  },
  "conceptos_operativos": [
    "SALIDA POR COBRO DE FLETE INICIAL",
    "SALIDA POR NUEVA ORDEN",
    "SALIDA DE COBRO DE DEVOLUCION POR ENTREGA NO EFECTIVA"
  ],

  "reglas_flete": {
    "modo": "PENDIENTE",
    "porcentaje": null,
    "valor_fijo_por_guia": null,
    "tabla_por_transportadora": {},
    "nota": "Completar en FASE 0. Ver §0.2."
  },

  "ventana_gracia_dias": 15,
  "tolerancia_valor": 50,
  "tolerancia_saldo": 1,
  "ventana_fecha_match_dias": 2
}
```

Los conceptos de arriba son **provisionales**. Los definitivos salen de la FASE 0 con el catálogo real en mano.

El matcheo de conceptos es **por contención, normalizado a mayúsculas y sin acentos**. Los textos de Dropi son plantillas con cola variable —el número de orden pegado al final— y cambian de redacción entre exportaciones. Un match exacto falla apenas cambia el sufijo.

---

## §8 · TABLAS PROPIAS DEL MOTOR

El núcleo ya tiene `movimientos`, `resultados`, `hallazgos`, `cargas`, `periodos` y `parametros_versiones`. Tu motor agrega solo lo suyo, en su propio esquema:

```sql
wallets.ordenes
  id, periodo_id, fuente_id,
  orden_id TEXT, guia TEXT, estatus TEXT, tipo_envio TEXT,
  transportadora TEXT, dropshipper_id TEXT,
  ganancia_esperada NUMERIC(18,2),
  valor_producto NUMERIC(18,2),
  fulfillment_esperado NUMERIC(18,2),
  flete_esperado NUMERIC(18,2),
  fecha_guia DATE, fecha_entrega DATE,
  lineas INT, crudo JSONB
  UNIQUE (periodo_id, fuente_id, orden_id)

wallets.matches
  id, movimiento_id BIGINT,        -- FK a la tabla del núcleo
  orden_id BIGINT,                 -- FK a wallets.ordenes
  nivel INT,                       -- 1 a 5, la cascada
  confianza TEXT,                  -- exacta | probable
  creado_por TEXT                  -- motor | usuario
```

`NUMERIC(18,2)` para todo lo monetario. **Nunca FLOAT para dinero.** Guardá siempre el `crudo`: si una regla cambia, se recalcula sin volver a pedir el archivo.

---

## §9 · PANTALLAS DEL MOTOR

El layout, la barra lateral, el selector de empresa y el encabezado los pone el núcleo. Tu motor aporta tres vistas dentro de ese marco:

**1. Carga y validación.** Dos zonas de carga —órdenes y wallet— y el resultado de C0 chequeo por chequeo. Si C0 bloquea, el botón de conciliar no se habilita. El mensaje dice qué falta y qué hacer, en castellano.

**2. Resumen del cierre.** El score arriba, los indicadores en pesos primero y conteos después, la serie histórica de los últimos meses, y un semáforo por regla.

**3. Detalle por regla.** Tabla de hallazgos con filtros por regla y estado, acciones en lote, y las columnas que de verdad importan: orden, guía, monto y **días transcurridos** —que es lo que decide si se reclama o se espera.

**Sistema visual, heredado de la plataforma:**

```
--navy #061428  --ink #0A1F3C  --blue #1B5FB0  --blue-soft #6FA8E8
--mist #EFF4FA  --border #D7E3F2  --white #FBFCFE  --text-2 #4E617C
--gold #FFC845 (SOLO alertas)  --ok #1B7F63  --crit #B5372F
```

Montserrat para todo, JetBrains Mono para identificadores, guías y montos en tabla.

**El color nunca dice solo.** Cada estado lleva su palabra: *Pagada*, *En ventana*, *Sin pago*, *Duplicada*, *No aplica*. Tiene que entenderse impreso en blanco y negro.

---

## §10 · TESTS

El paquete de reglas se prueba **primero y sin infraestructura**.

**El test de regresión es el más importante.** Con los archivos de julio en `fixtures/`, el motor debe devolver exactamente las cifras de §5. Escribilo antes de escribir las reglas y no cierres la fase hasta que pase.

Además: la cascada de emparejamiento nivel por nivel · agrupación por orden con múltiples líneas · la ventana de gracia en los bordes (día 14, 15 y 16) · los cuatro chequeos de C0 por separado · saldo descuadrado detectado · match por patrón con sufijo variable · una fuente sin reglas de cruce devuelve lista vacía sin error · aritmética con `Decimal` sin pérdida de precisión · el score calculado sobre un caso conocido.

Frontend: tests mínimos de la tabla de hallazgos y del formulario de carga.

---

## §11 · ORDEN DE FASES

Este motor es el **Bloque 1** del cronograma de la plataforma. Está previsto para dos semanas: la primera construye, la segunda corre un cierre real en producción.

**FASE 0 · Contrato de datos — sin código**
Leé los archivos de `fixtures/`. Perfilá columnas, estatus, tipos de envío y conceptos reales de las tres wallets. Proponé un `parametros.json` por wallet. Listá lo ambiguo. **PARÁ ACÁ** y esperá confirmación de los tres catálogos, la regla de flete y la regla de fulfillment por guía de Wiilog.

**FASE 1 · El paquete de reglas**
`parser.py`, `matcher.py` y `rules/c0.py` a `c6.py`, como Python puro sin dependencias del núcleo. **Escribí el test de regresión antes de las reglas.** Al terminar esta fase el motor debe reproducir las cifras de julio corriendo desde la línea de comandos, sin base de datos y sin servidor.

**FASE 2 · El enchufe**
Registrá el motor contra el contrato del núcleo. Las tablas propias, su migración, `validar()` y `ejecutar()` conectados, y los resultados escribiéndose donde el núcleo los espera. Verificá que la wallet de ASIATI devuelve lista vacía sin romperse.

**FASE 3 · Las pantallas**
Las tres vistas del §9 dentro del layout del núcleo, registradas en el registro del frontend.

**FASE 4 · Cierre real**
Correr el cierre del mes con datos reales de las tres wallets, ajustar parámetros con lo que aparezca, y documentar. El criterio de aceptación no es que el código funcione: es que **el equipo de conciliación confirme que el resultado representa correctamente la operación.**

---

## §12 · FORMA DE TRABAJAR

Antes de modificar archivos: inspeccioná lo que existe, no destruyas funcionalidad, planteá en una línea lo que vas a implementar, y después implementá.

Después de cada fase: corré los tests, mostrá qué archivos creaste o cambiaste, señalá las decisiones relevantes, y seguí si no hay bloqueo real.

No pidas confirmación para decisiones técnicas menores. Si encontrás algo que comprometa la integridad de los datos o la mantenibilidad, corregilo antes de continuar.

Antes de dar algo por terminado: corré los tests, revisá imports, verificá la migración. **No declares nada terminado si no lo validaste.**

**Interfaz, mensajes de error y nombres de campo visibles en castellano. Código, variables y commits en inglés.** Cada entrega va en su propia rama y entra por pull request.

### Lo que NO tenés que hacer

- No construyas nada del núcleo. La lista está en §2.
- No implementes la categorización en siete dimensiones: es del núcleo.
- No copies el motor para otra empresa. La empresa es configuración.
- No construyas la conciliación entre wallets todavía. Solo dejá el modelo preparado.
- No inventes conceptos de Dropi: los reales salen de la FASE 0.

Si algo del dominio no te queda claro, preguntá antes de asumir. Adivinar una regla de negocio cuesta más que preguntarla.
