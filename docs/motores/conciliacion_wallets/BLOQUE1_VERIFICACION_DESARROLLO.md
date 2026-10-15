# Bloque 1 · Verificación operativa de Wallets (solo lectura)

**Entorno declarado por el pipeline:** `https://3-141-226-208.sslip.io`
(instancia `financial-system-asiati-dev`, región `us-east-2`, en la
**cuenta AWS de ASIATI**). Verificar con acceso a esa cuenta: las sesiones
AWS de cuentas distintas no prueban ni descartan el estado de esta instancia.

## 1. Verificar endpoints HTTPS desde una red autorizada

```bash
python ops/verificar_desarrollo_wallets.py
```

Se exige HTTPS/TLS correcto y las respuestas exactas de los endpoints
`/health` y `/ready`. **Ambos endpoints devuelven hoy respuestas
estáticas** en `app/main.py`, por lo que el PASS acredita accesibilidad
de la API, no estado de PostgreSQL, Cognito ni conciliaciones.

## 2. Verificar SHA y contenedores desde la instancia ASIATI

En una sesión administrativa por el mecanismo autorizado de la cuenta
correcta (sin compartir claves, tokens ni configuración):

```bash
sudo cat /opt/financial-system/.release_commit
cd /opt/financial-system
sudo docker compose --env-file .env.production -f compose.production.yml ps
sudo docker compose --env-file .env.production -f compose.production.yml exec -T api alembic current
```

Comparar el SHA con `main` de GitHub y el número de migración con
`alembic/versions/` del mismo SHA. Registrar **solo** SHA, resultados
PASS/FAIL y referencias al run; no compartir la salida de archivos `.env`.

Validar en el servidor la **existencia no vacía** de
`WIILOG_WALLET_PRINCIPAL_EMAIL` sin imprimir, registrar o pegar su valor.
Comprobar también presencia de datos base por empresa, período y fuente
mediante la UI autenticada con acceso asignado.

## 3. Login, roles e interfaz

Con usuarios reales de desarrollo y sin copiar credenciales:

- Usuario conciliador: accede únicamente a empresas asignadas, ejecuta
  conciliaciones y gestiona los hallazgos permitidos.
- Coordinación Financiera: consulta evidencias, ve y resuelve escalados,
  administra catálogos según permisos.
- Perfil técnico: no dispone de facultades financieras por defecto.
- Recargar una conciliación válida: C0 y resumen se restauran de
  PostgreSQL, conforme al PR #143, sin mezclar empresas ni períodos.
- Período bloqueado/C0 inválido: no se visualiza como ejecución aceptada.
- Registrar latencia por wallet y operación, con hora y commit, sin
  incluir exportaciones ni cifras.

## 4. Regresiones financieras privadas (requisito de aceptación 5/5)

Con los Excel privados de septiembre 2026 disponibles en `fixtures/`
y parámetros resueltos de forma segura:

```bash
python ops/validar_regresion_privada_wallets.py
```

El ejecutor rechaza resultados FAIL y pruebas SKIP. Comprueba las cinco
wallets registradas en el alcance de septiembre, incluida la regresión
específica de Recompra Menpros. El baseline de Recompra se suministra
desde el paquete privado conforme a `BASELINE_PRIVADO.md`: no inferir
esperados de la corrida que se pretende evaluar.

## 5. Protección del repositorio y evidencias

A la fecha de esta revisión GitHub presenta el repositorio como
**público**, mientras las especificaciones y suites históricas contienen
resultados de casos operativos. Requiere atención del administrador:

1. **Prioridad:** revisar y restringir la visibilidad en GitHub
   (Settings → General → Danger Zone → Change repository visibility)
   si el contenido es de uso interno. Este cambio es administrativo,
   no lo realiza el PR.
2. Determinar qué cifras, identificadores y evidencia deben estar
   exclusivamente en almacenes privados; preservar copia íntegra
   autorizada antes de retirar contenido versionado.
3. Revisar también historia Git, forks, copias y logs: retirar datos de
   `main` no borra su historial público. Evaluar revocación/rotación
   si hubo credenciales expuestas y aplicar el procedimiento de
   remediación aprobado por seguridad.
4. Las nuevas pruebas evitan hacer `git add` de archivos de
   `fixtures/`, baselines reales y archivos de datos exportados;
   la política de resultados privados aplica también a logs y PRs.

## Evidencia mínima para cerrar Bloque 1

- Commit probado y commit instalado: deben coincidir.
- CI de unit/integration y validación HTTPS: PASS.
- Login Cognito, conexión operativa a PostgreSQL y roles: PASS.
- Las cinco regresiones privadas: PASS, cero SKIP, baselines intactos.
- UI de wallets y categorización persistente: PASS.
- Revisión de exposición de datos y decisión de confidencialidad:
  documentadas por responsable con autorización.

No realizar cierre de período, reapertura real, correcciones de saldo ni
cambios de baseline dentro de este bloque.
