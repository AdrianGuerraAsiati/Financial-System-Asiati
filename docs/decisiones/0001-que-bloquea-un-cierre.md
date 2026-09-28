# 0001 — Qué bloquea el cierre de un período

- Fecha: pendiente
- Decidió: pendiente (Juan Felipe, regla de negocio)
- Estado: Propuesta

## Contexto
El código actual (PR #12) impide cerrar un período mientras exista un hallazgo
crítico sin resolver. La SPEC no tiene esa regla: el cierre congela resultados y
los hallazgos siguen vivos, con memoria de justificación.

En wallets, `SIN_PAGO` es crítico y su resolución depende de que Dropi pague.
Si el cierre espera a que se resuelvan, el mes puede no cerrar nunca.

## Decisión
[pendiente] Opciones:
1. Mantener: ningún crítico abierto al cerrar.
2. Bloquear solo si C0 bloqueó alguna carga del período, o si hay críticos sin responsable asignado.
3. No bloquear: cerrar congela y los hallazgos pasan al período siguiente.

## Consecuencias
[pendiente]
