# 0002 — Estructura de carpetas del repositorio

- Fecha: pendiente
- Decidió: pendiente (Adrian + Juan Felipe)
- Estado: Propuesta

## Contexto
La SPEC §2 fija `backend/app/nucleo/` y `frontend/`. El repo arrancó con `app/core/`
en la raíz. El prompt maestro apunta a `backend/app/motores/conciliacion_wallets/`.

## Decisión
[pendiente] Recomendación: mover `app/`, `alembic/`, `tests/`, `pyproject.toml`,
`alembic.ini` y `Dockerfile` a `backend/` en un solo PR, antes de que exista el
frontend. Conservar el nombre `core` y actualizar la SPEC para que diga `core`.

## Consecuencias
Rutas del CI, del Dockerfile y de docker-compose cambian en el mismo PR.
