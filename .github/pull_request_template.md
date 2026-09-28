## Qué cambia
<!-- Una o dos frases. -->

## Por qué
<!-- Qué problema resuelve o qué regla implementa. Enlaza la sección de la SPEC o del prompt maestro. -->

## Cómo se probó
- [ ] Tests unitarios en verde
- [ ] Tests de integración en verde (si toca base de datos)
- [ ] Migración Alembic incluida y probada (si cambia un modelo)

## Regla de negocio que toca
<!-- Ninguna / C0…C6 / categorización / cierre de período… Si toca una, la revisa Juan Felipe. -->

## Revisión
- [ ] Sin secretos, `.env` ni datos reales de `fixtures/`
- [ ] Dinero en `Decimal` / `NUMERIC(18,2)`, nunca float
- [ ] Mensajes visibles en castellano y diciendo qué hacer
- [ ] Si se aparta de la SPEC, hay nota en `docs/decisiones/`

## Riesgos o pendientes
<!-- TODO(negocio) que queden abiertos. -->
