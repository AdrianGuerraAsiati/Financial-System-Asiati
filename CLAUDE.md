# Plataforma Financiera ASIATI — instrucciones para Claude Code

## Qué es este repo
Plataforma financiera del holding ASIATI (Colombia, Ecuador, Chile): un núcleo
compartido con motores enchufados encima. Cuatro dominios: conciliación, cartera,
tesorería, y cierres con estado de resultados. El primer motor es
`conciliacion_wallets`.

Fuentes de contexto y verdad. Léelas antes de cualquier cambio grande:
- `Ai_Handoff.md` — estado operativo vivo: qué está en curso, quién toca qué y próximos frentes. No reemplaza las decisiones formales.
- `docs/SPEC_NUCLEO.md` — el núcleo.
- `docs/motores/conciliacion_wallets/PROMPT_MAESTRO.md` — el motor de wallets (C0–C6).
- `docs/decisiones/` — decisiones tomadas después de la spec. Mandan sobre la spec y sobre el handoff.

Si el código y la spec no coinciden y no hay decisión escrita, dilo y pregunta.
No elijas en silencio.

## Quién es dueño de qué
- Núcleo, infraestructura, CI y migraciones: Adrian Guerra (@AdrianGuerraAsiati).
- Reglas de negocio de cada motor: Juan Felipe Parra (@juanparra-code).
- Si una tarea de motor necesita cambiar el núcleo, para: propón ese cambio como
  un PR aparte para el dueño del núcleo.

## Reglas que no se negocian
1. El motor es la unidad de código; la empresa es un dato. Nunca copies un motor por empresa.
2. Dinero: `NUMERIC(18,2)` en base de datos y `Decimal` en Python. Nunca float.
   Dentro de JSON, los montos van como texto decimal ("7300000.00").
3. Un período cerrado no se recalcula ni se modifica.
4. Los parámetros se versionan, nunca se sobrescriben.
5. Cada fila cargada guarda su `crudo` intacto.
6. La categorización en 7 dimensiones es del núcleo, no de un motor.
7. No inventes reglas de negocio, conceptos de Dropi ni cifras. Si falta un dato,
   escribe `TODO(negocio): <qué falta>` y pregunta.
8. No abstraigas para motores que no existen. El contrato `Motor` es provisional
   hasta el segundo motor.
9. Sin Redis, colas, microservicios ni Kubernetes.
10. Migraciones solo con Alembic. Nunca `create_all()`.

## Idioma
- Interfaz, mensajes de error y nombres de campo visibles: castellano, y el error
  dice qué hacer.
- Código, variables, commits y nombres de rama: inglés.

## Datos reales
- `fixtures/` tiene exportaciones reales de la operación y NO se sube a git.
- Los tests que usan datos reales llevan `@pytest.mark.fixtures_reales` y se saltan
  si los archivos no están.
- Nunca copies filas reales en commits, PRs, issues ni logs.

## Cómo se trabaja
- Una tarea = una rama corta desde `main`: `feat/…`, `fix/…`, `docs/…`,
  `refactor/…`, `test/…`, `chore/…`.
- Test primero, luego código. Un PR pequeño por comportamiento.
- Commits en Conventional Commits, en inglés: `feat(wallets): add C1 paid-profit rule`.
  Usa el alcance: `core`, `wallets`, `ci`, `docs`.
- Nunca hagas push a `main`, nunca `--force`. Todo entra por PR con CI verde.
- Antes de decir que algo está terminado:
  - Unitarios: `pytest -q tests --ignore-glob="tests/test_core_*.py"`
  - Integración: `docker compose up -d db`, `alembic upgrade head`, `pytest -q tests/test_core_*.py`
  - Si cambiaste un modelo, hay migración nueva y `alembic upgrade head` corre limpio.
  - El diff no tiene secretos, `.env`, ni datos reales.
- Si algo compromete la integridad de los datos, la seguridad o la mantenibilidad,
  dilo antes de seguir.

## Comandos del proyecto
- `/fase <n>` — ejecuta una fase del prompt maestro de wallets y para.
- `/pr` — valida, hace commit y abre el pull request de la rama actual.
- `/release <versión>` — prepara una versión: changelog, número, tag y release.
- `/revisar-spec` — compara el código contra la SPEC y lista diferencias, sin tocar código.

## Estado actual · 30-sep-2026

Antes de iniciar trabajo, leer `docs/ESTADO_DESARROLLO_2026-09-30.md`.

Resumen vigente:

- desarrollo desplegado en AWS Lightsail;
- Compras funciona temporalmente con **S3 privado -> copia operacional local -> snapshot PostgreSQL**, no con Google Sheets directo;
- snapshot de Compras de desarrollo válido: 2.260 líneas;
- Google Sheets queda pendiente de acceso administrativo de Google Cloud;
- #89 de wallets tienda/pagos está fusionado;
- #86 de sanitización de Wallets está fusionado y los identificadores reales se inyectan por runtime;
- #91 de movimientos/categorización es el único PR funcional abierto y sigue en draft por una decisión de contrato;
- Cartera sigue sin fuente real identificada; no usar el Excel de Compras como sustituto.

No asumir que las secciones históricas de `Ai_Handoff.md` sobre autenticación Google o fuente viva describen el entorno desplegado actual; la actualización del 30-sep al inicio de ese archivo y el reporte anterior mandan para estado operativo.

