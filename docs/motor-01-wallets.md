# Motor 01 · Conciliación de Wallets

> **Nota de vigencia · 29-sep-2026:** este archivo conserva contexto histórico del Motor 01, pero ya no es la fuente operativa principal para Wiilog. Las secciones que presentan fulfillment, flete y validación Wiilog como pendientes quedaron superadas por `docs/motores/conciliacion_wallets/WALLET_WIILOG.md`, `PROMPT_MAESTRO.md`, `parametros_wallet_wiilog.json` y el código/tests actuales. La referencia 1.555 / 28 / 80 permanece como baseline histórico hasta identificar y conectar su dataset; no debe confundirse con la regresión Wiilog de septiembre 2026.

## Estado según las fuentes del proyecto

Este es el primer motor que debe llegar a producción.

La arquitectura y las reglas fueron validadas con datos reales. El motor debe construirse sobre ese conocimiento existente y no redefinir el proceso desde cero.

## Objetivo

Recibir las fuentes requeridas del período, validar su integridad, ejecutar las reglas de conciliación y producir únicamente los casos que requieren resolución humana.

La operación objetivo es:

1. cargar archivo;
2. validar;
3. clasificar y cruzar;
4. dejar en bandeja las diferencias;
5. resolver únicamente los casos dudosos;
6. cerrar el período cuando no existan diferencias críticas abiertas.

## Criterio de aceptación conocido

El motor debe reproducir los resultados obtenidos sobre el caso real utilizado durante el levantamiento:

- 1.555 no pagadas;
- 28 duplicadas;
- 80 huérfanas.

Si no reproduce esos resultados sobre el mismo conjunto de entrada, el motor no se considera equivalente.

## Evidencia previa

Durante la validación con datos reales se obtuvieron:

- 7 conciliaciones;
- 6 correcciones al diseño original.

Esto significa que el comportamiento real debe gobernar el diseño del motor.

## Descubrimiento de reglas de Wallets

La evidencia operativa más reciente confirma que la conciliación de Wallets contiene varias reglas y que todavía no todas están construidas/documentadas.

### Regla identificada parcialmente: guías entregadas

La transcripción disponible indica que existe una regla asociada a las **guías entregadas** y al **día/hora en que fueron entregadas**.

La evidencia disponible no permite determinar todavía de forma inequívoca:

- cuál es el dato fuente exacto que identifica una guía entregada;
- qué timestamp debe tomarse como referencia;
- cómo se normaliza la hora;
- qué significa exactamente el corte mencionado como “00:00 del día que se entregaron”;
- qué movimiento o valor se reconoce a partir de ese corte;
- qué excepciones existen;
- qué resultado debe producir el motor cuando la condición se cumple o falla.

Por tanto, esta regla **no debe implementarse todavía**.

### Plantilla mínima para cerrar una regla

Antes de convertir una regla de Wallets en código TDD se debe poder responder:

1. **Nombre funcional de la regla.**
2. **Fuentes de entrada.**
3. **Campos usados.**
4. **Condición exacta.**
5. **Transformación o cálculo.**
6. **Resultado esperado.**
7. **Excepciones.**
8. **Ejemplo positivo real.**
9. **Ejemplo negativo real.**
10. **Cómo impacta no pagadas, duplicadas, huérfanas u otra categoría.**

Cuando esos diez puntos estén suficientemente definidos, la regla puede pasar a un PR RED → GREEN.

## Pendientes de negocio antes de cerrar las reglas

Todavía deben levantarse:

1. tres catálogos de conceptos, uno por wallet;
2. regla de comisión de flete:
   - porcentaje;
   - valor fijo;
   - o tabla por transportadora;
3. forma en que Wiilog cobra fulfillment por guía y su regla de conciliación.

Estos puntos no deben inventarse en código.

## Categorización

La capa de categorización no pertenece exclusivamente a Wallets.

Fue identificada como una capacidad del core porque las dimensiones de categorización serán consumidas por varios motores y posteriormente por flujo de caja y resultados.

El Motor 01 puede consumir esa interfaz, pero no debe crear una implementación paralela propia.

### Aclaración sobre el documento largo

La evidencia operativa más reciente aclara que el archivo largo mencionado en conversación corresponde a la **categorización de movimientos bancarios**, no al detalle completo de las reglas de Wallets.

Se describe como una referencia de aproximadamente 24 páginas sobre la forma actual de categorizar movimientos bancarios, con alrededor de 20 columnas/dimensiones.

Ese material pertenece al levantamiento de categorización y debe tratarse por separado del descubrimiento de reglas de Wallets.

## Validación de archivos

Antes de ejecutar reglas de conciliación, la carga debe poder detectar archivos incompletos o inválidos y bloquear su procesamiento.

La forma exacta de validación se definirá con el contrato de datos real de Wallets.

## Empresa

No se crearán copias del motor por empresa.

La empresa debe ser configuración/dato de ejecución. El mismo motor se reutiliza para las distintas líneas de negocio con parámetros diferentes.

## Contrato técnico

El contrato actual de `Motor` es provisional.

Debe revisarse después de construir el segundo motor. Solo en ese momento se debe promover al core aquello que demuestre ser realmente común.

## Fuera de alcance por ahora

No implementar todavía dentro de este motor:

- conciliación bancaria;
- cartera;
- última milla;
- Chin Chin;
- flujo de caja;
- tesorería;
- OCR de MAJO;
- WhatsApp;
- Siigo;
- reglas no documentadas en las fuentes.

Esos elementos se incorporarán únicamente cuando corresponda por dominio o cuando el análisis del sistema legado demuestre que una pieza debe reutilizarse.
