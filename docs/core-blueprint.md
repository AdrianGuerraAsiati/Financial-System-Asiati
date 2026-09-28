# Bosquejo del núcleo · Plataforma Financiera ASIATI

## Propósito

La plataforma se construye como un **monolito modular**: un solo sistema desplegable, con un núcleo compartido y módulos de negocio independientes.

El núcleo no contiene reglas particulares de conciliación, cartera, tesorería o cierres. Su responsabilidad es ofrecer capacidades comunes para que esos módulos operen con el mismo contexto, trazabilidad y controles.

## Regla de frontera

La regla de diseño es:

- si una capacidad es usada de forma real por dos o más módulos, puede pertenecer al núcleo;
- si solo la necesita un módulo, permanece dentro de ese módulo;
- si todavía hay duda, permanece en el módulo hasta tener evidencia para promoverla al núcleo.

El objetivo es evitar un `core` convertido en un módulo gigante y evitar abstracciones prematuras.

---

## 1. Qué ya existe en el núcleo

### Empresas

**Estado:** implementado.

Responsabilidad:

- representar las empresas que operan sobre la misma plataforma;
- permitir que los módulos se ejecuten con contexto empresarial sin copiar código por empresa.

Ubicación actual:

- `app/core/empresas.py`.

### Fuentes

**Estado:** implementado.

Responsabilidad:

- identificar el origen lógico de una carga;
- relacionar cada fuente con su empresa.

Ubicación actual:

- `app/core/fuentes/`.

### Períodos y cierres

**Estado:** implementado.

Responsabilidad:

- definir períodos financieros por empresa;
- mantener estado abierto/cerrado;
- impedir cambios de rango sobre períodos cerrados;
- registrar cierre y reapertura;
- exigir motivo para una reapertura;
- impedir el cierre cuando existen hallazgos críticos abiertos.

Ubicación actual:

- `app/core/periodos/`.

### Cargas

**Estado:** base implementada.

Responsabilidad actual:

- asociar una carga con empresa, fuente y período;
- calcular un hash SHA-256 del contenido;
- evitar registrar el mismo contenido dos veces para una misma empresa;
- validar que fuente y período pertenezcan a la empresa indicada.

Ubicación actual:

- `app/core/cargas/`.

Todavía no pertenece a esta capacidad decidir:

- qué columnas exige Wallets;
- qué formato exige Chin Chin;
- cómo se interpreta un archivo de cartera;
- reglas particulares de parsing o normalización de un módulo.

### Hallazgos

**Estado:** implementado como base compartida.

Responsabilidad:

- representar diferencias o situaciones que requieren revisión;
- indicar si son críticas y si están resueltas;
- registrar motor, regla, descripción y evidencia estructurada;
- servir como gate compartido para el cierre de períodos.

Ubicación actual:

- `app/core/hallazgos/`.

### Usuarios y roles

**Estado:** base implementada.

Roles definidos para la primera versión:

- super administrador;
- coordinación financiera;
- conciliación.

Responsabilidad actual:

- persistir usuarios;
- registrar su rol;
- mantener estado activo/inactivo;
- impedir altas con roles no definidos.

Ubicación actual:

- `app/core/usuarios/`.

Todavía están pendientes autenticación y permisos efectivos.

### Contrato de motor

**Estado:** provisional.

Responsabilidad:

- ofrecer una forma mínima de identificar, validar y ejecutar motores;
- producir resultados explicables.

Ubicación actual:

- `app/core/motor.py`.

Este contrato no debe considerarse definitivo hasta tener un segundo motor funcional.

---

## 2. Qué debe quedarse en el núcleo

Estas capacidades pertenecen al núcleo porque atraviesan varios procesos y no representan una regla particular de negocio de un solo módulo.

| Capacidad | Estado | Razón |
| --- | --- | --- |
| Empresas | Implementado | Todos los módulos operan bajo una empresa |
| Usuarios y roles | Base implementada | Control de acceso transversal |
| Períodos y cierres | Implementado | Compartido por conciliaciones, cartera y reportes |
| Fuentes | Implementado | Origen común de información |
| Cargas e idempotencia | Base implementada | Los módulos reciben información usando la misma trazabilidad |
| Hallazgos | Implementado | Bandeja común de diferencias y control de cierre |
| Parámetros versionados | Pendiente | Reglas configurables deben conservar versión y vigencia |
| Auditoría transversal | Parcial | Cierres ya tienen historial; falta auditoría general |
| Exportación | Pendiente | Capacidad común para sacar resultados |
| Categorización compartida | Pendiente de contrato | Se usará por más de un proceso; no debe duplicarse por motor |
| Registro/descubrimiento de módulos | Pendiente | Permite que la aplicación conozca módulos sin acoplarlos entre sí |

### Lo que NO debe vivir en el núcleo

El núcleo no debe conocer:

- cómo Dropi concilia una wallet;
- qué hace que una guía sea pagada o no pagada;
- cómo Chin Chin cruza ventas y recaudos;
- cómo se calcula la comisión de flete;
- cómo se concilia fulfillment por guía;
- cómo se determina el saldo de una cuenta por cobrar;
- cómo se cruza un extracto con el libro contable;
- quién aprueba un pago de tesorería;
- cómo se calcula un indicador particular de cierre.

---

## 3. Qué pertenece a cada módulo

### `conciliacion_wallets`

Responsabilidad:

- contrato de datos de las wallets;
- validaciones específicas de sus archivos;
- normalización propia;
- reglas de cruce;
- catálogos propios de cada wallet cuando sean particulares de este motor;
- comisión de flete cuando sea una regla propia de Wallets;
- detección de no pagadas, duplicadas, huérfanas y demás resultados definidos;
- tablas propias de órdenes y matches cuando se necesiten;
- evidencia específica de cada resultado.

**No debe implementar:** usuarios, períodos, cargas generales, auditoría general ni una segunda bandeja de hallazgos.

### `conciliacion_chin_chin`

Responsabilidad:

- fuentes propias de ventas y recaudos;
- validaciones del contrato de datos;
- reglas para cruzar ventas contra datáfono, transferencias, efectivo u otras fuentes definidas;
- excepciones y evidencia específica del proceso.

**Estado:** pendiente de levantamiento.

### `cartera_ocs`

Responsabilidad:

- cuentas/documentos por cobrar;
- facturas y órdenes de compra;
- saldos, vencimientos, monedas y seguimiento;
- aplicación de pagos y reglas propias de cartera;
- datos/documentos que se recuperen de MAJO y pertenezcan al dominio.

Cartera puede compartir períodos, hallazgos, usuarios y auditoría con el núcleo, pero sus documentos no deben convertirse en tablas genéricas del core.

**Estado:** pendiente de levantamiento y análisis de MAJO.

### `recaudos_ultima_milla`

Responsabilidad:

- recaudos asociados a operación de última milla;
- fulfillment por guía;
- reglas de cruce y excepciones propias de Wiilog;
- evidencia de diferencias.

**Estado:** pendiente de levantamiento.

### `conciliacion_bancos`

Responsabilidad:

- contrato de extractos bancarios y libro contable;
- normalización bancaria específica;
- matching entre movimientos;
- reglas y tolerancias propias de conciliación bancaria;
- excepciones del proceso.

Puede consumir una capacidad compartida de categorización, pero no debe convertir las reglas particulares de matching bancario en reglas del core.

**Estado:** pendiente de mapeo.

### Tesorería

**Estado arquitectónico:** decisión pendiente.

Tesorería es un flujo de negocio explícito: solicitud, aprobación, pago, soporte y trazabilidad. Por ese motivo **no pertenece al núcleo**.

Antes de construirlo se debe decidir, con el mapeo del proceso, si:

1. queda como un módulo propio `tesoreria`; o
2. forma un mismo bounded context con bancos, manteniendo internamente responsabilidades separadas.

No se tomará esa decisión antes del mapeo del flujo.

### `flujo_caja` / cierres y resultados

Responsabilidad:

- consultar información ya procesada por los demás módulos;
- consolidar resultados;
- producir flujo de caja y reportes acordados con Finanzas;
- permitir drill-down hacia la información fuente.

No debe recalcular las conciliaciones ni copiar reglas de los motores operativos.

**Estado:** pendiente de levantamiento con Finanzas.

---

## 4. Dependencias permitidas

La dirección deseada es:

```text
módulos de negocio
      ↓
APIs públicas del core
      ↓
persistencia / infraestructura
```

Un módulo puede consumir capacidades públicas del núcleo.

El núcleo **no** debe importar motores ni depender de reglas de Wallets, Chin Chin, Cartera, Bancos o Tesorería.

Los módulos tampoco deben importar modelos internos de otros módulos para reutilizar lógica. Cuando exista una necesidad real de colaboración entre dos módulos, se debe definir una interfaz explícita o promover al núcleo únicamente la capacidad verdaderamente compartida.

---

## 5. Estado del núcleo frente a la primera versión web

### Ya disponible

- empresas;
- fuentes;
- períodos;
- cierre/reapertura e historial;
- hash e idempotencia de cargas;
- coherencia empresa/fuente/período;
- hallazgos críticos y explicables;
- bloqueo de cierre por hallazgos críticos;
- usuarios y catálogo inicial de roles;
- PostgreSQL + Alembic;
- pruebas unitarias e integración en CI.

### Pendiente antes o durante la primera versión

- autenticación real;
- permisos efectivos por rol;
- recepción de archivos desde la aplicación web;
- almacenamiento definitivo de archivos;
- parámetros versionados;
- auditoría transversal;
- exportaciones;
- registry/app shell de módulos;
- despliegue productivo, dominio, TLS y backups.

Estos pendientes se implementarán en cortes pequeños y solo con el nivel necesario para soportar los módulos que entren en producción.

---

## 6. Decisiones que todavía NO están cerradas

1. Proveedor/mecanismo de autenticación.
2. Matriz exacta de permisos de los tres roles.
3. Almacenamiento definitivo de archivos cargados.
4. Contrato de categorización compartida.
5. Estructura definitiva de parámetros versionados.
6. Si Tesorería será módulo propio o bounded context conjunto con Bancos.
7. Contrato definitivo de `Motor`, que se revisará con el segundo motor funcional.
8. Alcance exacto de auditoría general.
9. Alcance y formato de exportaciones.

Estas decisiones se resuelven cuando exista evidencia del proceso que las necesita; no se completan por anticipado.

---

## 7. Siguiente secuencia de construcción del núcleo

Con el bosquejo cerrado, el orden recomendado para soportar la primera versión web es:

1. permisos mínimos de los tres roles;
2. recepción y trazabilidad de archivos desde la aplicación;
3. almacenamiento de archivos con una interfaz sustituible;
4. app shell / registry de módulos;
5. parámetros versionados cuando la primera regla configurable lo requiera;
6. auditoría adicional al aparecer la primera acción operativa que deba rastrearse;
7. exportación al aparecer el primer resultado que operación necesite descargar.

La lógica real de Wallets, Chin Chin y Cartera se desarrolla dentro de sus módulos y no debe esperar a que todo el núcleo esté completo.
