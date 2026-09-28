# 0004 — Endpoints de Wiilog sin autenticación, solo temporalmente

- Fecha: 2026-09-28
- Decidió: Juan Felipe Parra
- Estado: Aceptada

## Contexto
`docs/nucleo/ROLES_Y_PERMISOS.md §7` exige que cada endpoint revise permisos en el
backend con `Depends(requiere(...))`. Los endpoints de la wallet Wiilog que entraron
en el PR #42 (`POST /wallets/wiilog/conciliar` y `GET /wallets/wiilog/hallazgos`,
en `app/motores/conciliacion_wallets/wiilog/api.py`) no piden sesión. La sesión de
usuarios, roles y permisos crea `requiere(...)`, pero la pantalla de login llega
después. Protegerlos ahora deja inutilizable la pantalla actual.

## Decisión
Los endpoints de Wiilog quedan sin autenticación solo mientras no exista la
pantalla de login. Se protegen con `requiere(...)` en el mismo PR de esa pantalla.
La plataforma NO se publica en internet hasta que estén protegidos.

## Consecuencias
- Mientras tanto la plataforma solo corre en local o en una red privada.
- El PR de la pantalla de login debe proteger `conciliar` con
  `requiere("conciliacion.ejecutar", empresa_de=...)` y `hallazgos` con
  `requiere("conciliacion.ver", empresa_de=...)`, y mover las rutas bajo `/api/v1`.
- Ningún despliegue público se hace mientras esta decisión siga vigente.
