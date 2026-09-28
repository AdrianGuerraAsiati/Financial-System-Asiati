---
description: Prepara y publica una versión (changelog, número de versión, tag y release en GitHub)
argument-hint: <versión exacta, ej. 0.2.0>
---
Vas a preparar la versión v$ARGUMENTS. Son dos pasos y paras entre ellos.

PASO A — Preparar (por PR)
1. `git switch main` y `git pull`. Confirma con `gh run list --branch main --limit 1`
   que el último CI de `main` está verde. Si no, para.
2. Lista lo que entra: `git log <último tag>..HEAD --oneline` (si no hay tags, desde el inicio).
3. Crea la rama `chore/release-v$ARGUMENTS`.
4. Cambia `version` en `pyproject.toml` a $ARGUMENTS.
5. Agrega la sección `## [$ARGUMENTS] - <fecha de hoy>` arriba en `CHANGELOG.md`,
   en castellano, para alguien no técnico, agrupada en: Agregado, Cambiado, Corregido,
   Eliminado. Mueve ahí lo que haya en `[Sin publicar]`.
6. Actualiza "Estado actual" en `CLAUDE.md`.
7. Abre el PR `chore(release): v$ARGUMENTS` y PARA. Espera a que yo te diga que está fusionado.

PASO B — Publicar (solo cuando yo lo pida)
8. `git switch main` y `git pull`.
9. `git tag -a v$ARGUMENTS -m "v$ARGUMENTS"` y `git push origin v$ARGUMENTS`.
10. `gh release create v$ARGUMENTS --title "v$ARGUMENTS — <nombre del hito>" --notes "<la sección del CHANGELOG>"`.
11. Muestra el enlace del release.
