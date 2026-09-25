# Motor 01 · Conciliación de Wallets

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
