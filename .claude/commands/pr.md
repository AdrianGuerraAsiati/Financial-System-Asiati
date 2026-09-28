---
description: Valida la rama actual, hace commit y abre el pull request
---
1. Confirma que la rama actual no es `main`. Si lo es, para.
2. Corre los tests unitarios. Si hay base de datos disponible, también los de integración.
   Si algo falla, muéstralo y para.
3. Revisa `git diff main...HEAD` y confirma:
   - sin secretos, sin `.env`, sin archivos de `fixtures/` ni filas de datos reales;
   - sin `float` para dinero;
   - si cambió un modelo, hay migración Alembic nueva;
   - si el cambio se aparta de la SPEC, hay nota en `docs/decisiones/`.
4. Haz los commits pendientes en inglés con Conventional Commits.
5. `git push -u origin <rama>`.
6. Abre el PR contra `main` con `gh pr create --base main`, título en Conventional Commits
   y cuerpo siguiendo `.github/pull_request_template.md`, escrito en castellano.
7. Muestra el enlace del PR y `gh pr checks`.
