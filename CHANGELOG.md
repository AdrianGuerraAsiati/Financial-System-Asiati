# Registro de cambios

Todos los cambios relevantes de la Plataforma Financiera ASIATI.
Formato: [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Numeración: [SemVer](https://semver.org/lang/es/) — 0.x mientras no haya un cierre real aceptado.

## [Sin publicar]

### Agregado
- Kit de trabajo con Claude Code: CLAUDE.md, comandos en `.claude/`, CODEOWNERS y plantilla de PR.
- Motor de referencia de la wallet Wiilog (Python puro) con pruebas sintéticas y regresión de septiembre 2026.
- Marcador `fixtures_reales` registrado en `pyproject.toml`.

### Corregido
- Avisos de obsolescencia de `pd.Timedelta` en el motor Wiilog, sin cambiar resultados.

## [0.1.0] - 2026-09-25

Primera base del núcleo. Todavía no concilia nada.

### Agregado
- Proyecto Python con FastAPI, PostgreSQL 16 y migraciones Alembic; entorno local con Docker Compose.
- CI en GitHub Actions: pruebas unitarias y de integración contra PostgreSQL en cada PR.
- Empresas y fuentes de datos (por ejemplo, "la wallet de Wiilog").
- Períodos por empresa con cierre y reapertura auditados; la reapertura exige motivo.
- Un período cerrado no permite cambiar sus fechas.
- El cierre se bloquea si hay hallazgos críticos abiertos (regla por confirmar).
- Registro de cargas con huella SHA-256: el mismo archivo no se carga dos veces en la misma empresa.
- Hallazgos explicables: motor, regla, descripción y evidencia.
- Esqueleto del motor de conciliación de wallets: rechaza cargas vacías.
