# Sistema visual V1 — Plataforma Financiera ASIATI

**Estado:** implementado  
**Alcance:** shell web, login, Inicio, Cartera y Compras  
**Regla:** esta capa no cambia fórmulas, contratos, permisos ni decisiones financieras.

## Objetivo

La interfaz debe sentirse como una herramienta financiera interna seria:

- limpia;
- sobria;
- densa cuando hay datos, pero no saturada;
- consistente entre módulos;
- fácil de escanear;
- usable en escritorio y móvil;
- sin decoración que compita con la información.

## Dirección visual

La V1 toma como referencia la identidad pública actual de ASIATI: azul profundo, amarillo brillante, superficies limpias y una narrativa corporativa centrada en estructura, método, control y visión global.

La referencia pública utilizada es el sitio corporativo actual y sus piezas visuales. No se encontró un manual de marca público con valores HEX oficiales, por lo que los colores del producto se consideran **aproximaciones provisionales** hasta recibir el brand book o archivos maestros.

Paleta de producto provisional:

```css
--asiati-blue: #005b8f;
--asiati-blue-deep: #003f64;
--asiati-yellow: #f4cf22;
--asiati-yellow-soft: #fff8d7;
```

Uso:

- azul ASIATI: marca, navegación seleccionada, acciones primarias y foco;
- amarillo ASIATI: acento de marca, no semántica financiera;
- neutros: fondos, superficies, tablas y estructura;
- verde/ámbar/rojo: permanecen reservados para estados técnicos/operativos ya definidos.

Principios:

1. **Jerarquía antes que color.** Tamaño, peso, espacio y agrupación deben explicar la estructura.
2. **Color con función.** Azul ASIATI = acción/selección; amarillo ASIATI = identidad/acento; verde = disponible/correcto; ámbar = revisión; rojo = error.
3. **Superficies contenidas.** Cards blancas con bordes finos y sombras discretas.
4. **Datos primero.** Tablas, KPIs y estados deben tener alta legibilidad.
5. **Movimiento mínimo.** Solo transiciones cortas de interacción; se respeta `prefers-reduced-motion`.
6. **Sin dependencia de fuentes externas.** Se utiliza la pila tipográfica del sistema.

## Tokens principales

Definidos en `app/web/styles.css`:

```css
--asiati-blue
--asiati-blue-deep
--asiati-yellow
--asiati-yellow-soft
--bg
--surface
--ink
--ink-soft
--muted
--line
--nav
--accent
--success
--warning
--danger
--shadow-xs
--shadow-sm
--shadow-md
--radius-sm
--radius-md
--radius-lg
--radius-xl
```

Los módulos nuevos deben reutilizar estos tokens antes de introducir colores o medidas propias.

## Shell

### Identidad ASIATI

El shell utiliza:

- `ASIATI · 360°` como firma compacta;
- `Plataforma Financiera` como descriptor de producto;
- `Método · Control · Datos` como mantra interno del shell;
- el amarillo como gesto de marca discreto en el monograma y selección activa.

No se recrea ni se sustituye el logotipo corporativo oficial. El monograma CSS es un identificador de producto interno hasta disponer de los assets de marca aprobados.

### Topbar

Contiene:

- marca ASIATI;
- nombre de la plataforma;
- selector de empresa;
- usuario;
- salida.

En escritorio permanece visible al hacer scroll.

### Sidebar

Separa:

- `Workspace`: módulos disponibles;
- `Próximamente`: módulos todavía deshabilitados.

El estado activo combina azul ASIATI con un acento amarillo fino. El amarillo no implica prioridad, riesgo ni éxito.

En pantallas pequeñas se convierte en navegación horizontal.

## Login

El login conserva una sola acción primaria y una composición centrada.

Se usa:

- marca;
- título claro;
- copy breve;
- inputs de altura cómoda;
- fondo con textura geométrica muy sutil.

No requiere imágenes ni assets externos.

## Cards y paneles

### Panel

Uso: bloques de trabajo con título, contexto y contenido.

### Executive metric card

Uso: KPIs o conteos prominentes.

No debe utilizarse para métricas cuya definición de negocio aún esté abierta.

### Home module card

Uso: resumen de cada módulo en Inicio.

Debe contener:

- nombre;
- disponibilidad;
- 2–4 métricas;
- acción de navegación si existe.

## Tablas

Las tablas:

- se presentan dentro de una superficie delimitada;
- usan encabezados de bajo contraste;
- mantienen separación por filas;
- tienen hover muy sutil;
- permiten scroll horizontal en móvil.

No colorear filas completas para indicar estados salvo que exista una semántica aprobada.

## Formularios

Inputs y selects usan:

- mismo radio;
- mismo borde;
- focus ring azul;
- labels compactos;
- controles de al menos ~38px de altura.

## Estados

Semántica visual:

- `success`: fuente disponible / operación correcta;
- `warning`: revisión;
- `danger`: error técnico/validación;
- neutral: información sin valoración.

No convertir una categoría de negocio en rojo/verde sin una regla aprobada.

## Responsive

Breakpoints principales:

- 1100px: reduce shell y grids;
- 850px: sidebar pasa a navegación horizontal;
- 620px: cards, paneles, filtros y acciones pasan a una columna.

## Accesibilidad

La V1 incluye:

- `:focus-visible` consistente;
- contraste alto en texto principal;
- áreas táctiles razonables;
- `prefers-reduced-motion`;
- navegación funcional sin depender únicamente del color.

## Evolución

Antes de añadir un componente visual nuevo:

1. comprobar si existe un patrón equivalente;
2. reutilizar tokens;
3. documentar semántica si introduce estados;
4. mantener la lógica en JS/backend, no en CSS;
5. validar escritorio y móvil.


## Lenguaje de marca

La interfaz puede reutilizar conceptos públicos de ASIATI cuando aporten contexto, especialmente:

- Ecosistema 360°;
- método;
- control;
- visión global;
- cultura de datos y resultados;
- estructura y trazabilidad.

No convertir lenguaje comercial del sitio público en una regla financiera o KPI. La identidad verbal acompaña al producto; no define la lógica del negocio.
