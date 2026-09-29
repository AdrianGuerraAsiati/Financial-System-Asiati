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

La V1 usa una base neutra clara con navegación oscura y un único acento azul.

Principios:

1. **Jerarquía antes que color.** Tamaño, peso, espacio y agrupación deben explicar la estructura.
2. **Color con función.** Azul = acción/selección; verde = disponible/correcto; ámbar = revisión; rojo = error.
3. **Superficies contenidas.** Cards blancas con bordes finos y sombras discretas.
4. **Datos primero.** Tablas, KPIs y estados deben tener alta legibilidad.
5. **Movimiento mínimo.** Solo transiciones cortas de interacción; se respeta `prefers-reduced-motion`.
6. **Sin dependencia de fuentes externas.** Se utiliza la pila tipográfica del sistema.

## Tokens principales

Definidos en `app/web/styles.css`:

```css
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

El estado activo usa acento azul, no un fondo completamente diferente.

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
