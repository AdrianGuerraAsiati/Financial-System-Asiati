---
description: Ejecuta una fase del prompt maestro del motor de wallets y para al terminar
argument-hint: <número de fase, 0 a 4>
---
Lee `docs/motores/conciliacion_wallets/PROMPT_MAESTRO.md`, `docs/SPEC_NUCLEO.md`
y lo que haya en `docs/decisiones/`.

Vas a ejecutar ÚNICAMENTE la FASE $ARGUMENTS.

Antes de escribir código:
1. Si estás en `main`, crea una rama `feat/wallets-fase-$ARGUMENTS-<tema-corto>`.
2. Revisa los bloqueantes de §0 que afectan esta fase. Si alguno la bloquea, dilo y para.
3. Si la fase necesita `fixtures/` y los archivos no están, dilo y para.
4. Dime en cinco líneas qué vas a hacer.

Durante la fase: test primero, commits pequeños en inglés con Conventional Commits.

Al terminar:
- Corre los tests y muestra el resultado.
- Lista los archivos creados o cambiados.
- Señala las decisiones que tomaste y cada `TODO(negocio)` que dejaste.
- No sigas con la fase siguiente. Sugiere usar `/pr`.
