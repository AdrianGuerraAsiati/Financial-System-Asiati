# Listas de categorización (7 dimensiones)

Decisión de negocio: `docs/decisiones/0008-categorizacion-manual-wallets.md` (Juan Felipe Parra, 6-oct-2026).
La categorización en 7 dimensiones es del núcleo (CLAUDE.md, regla 6).

| Dimensión | Cómo se llena |
|---|---|
| Ingreso/egreso | Lista administrable |
| Unidad de negocio | Lista administrable |
| Categoría (concepto) | Lista administrable |
| Empresa | Lista administrable; al categorizar un movimiento es la de la wallet y no se edita |
| Fijo/variable | Lista administrable |
| Modalidad | Fija: WALLET |
| Tercero | Único texto libre (puede ir vacío) |

## Tabla y permisos

- Tabla `dimension_valores` (migración `0018_dimension_valores`): `dimension`, `valor`, `valor_normalizado`, `activo`.
  Único por `(dimension, valor_normalizado)`: "Consultoría" y "CONSULTORIA " son el mismo valor.
- Los valores son **globales** (aplican a todas las empresas) y **nunca se borran**: se desactivan. Lo ya
  categorizado conserva el texto con el que se guardó y el `id` del valor.
- `dimensiones.gestionar` (superadmin y coordinador financiero): agregar, renombrar, desactivar y activar. Cada cambio
  queda en auditoría (`dimension.crear`, `dimension.actualizar`).
- `parametros.ver`: leer las listas (lo usa el formulario del conciliador).

## Endpoints

```text
GET    /api/v1/dimensiones?dimension=categoria&incluir_inactivos=false   parametros.ver
POST   /api/v1/dimensiones          {dimension, valor}                    dimensiones.gestionar
PATCH  /api/v1/dimensiones/{id}     {valor?, activo?}                     dimensiones.gestionar
POST   /api/v1/hallazgos/{id}/observar   {observacion, resolver, categorizacion?}
```

`categorizacion` exige además `movimientos.categorizar`. Se valida contra los valores **activos** y se guarda en
`hallazgo.evidencia.categorizacion` con el valor de la lista, su `id` (`valor_ids`), quién y cuándo. Si un valor no
está, la respuesta es 422 y dice que se elija uno de la lista o se escale al coordinador. La clave estable de
hallazgos (`HALLAZGOS_CLAVE_ESTABLE.md`) conserva la categorización al reconciliar.

## Carga inicial

```bash
python -m app.core.dimensiones --archivo docs/nucleo/dimensiones_iniciales.json
```

Idempotente: crea lo que falta y no toca lo existente (no renombra ni reactiva). Contenido de
`dimensiones_iniciales.json`:

- Ingreso/egreso: INGRESO, EGRESO, NETO_CERO, TRASLADO.
- Unidades de negocio (19): FF, UM, TIENDAS, PROVEEDURIA, TRANSFER INTERCOMPANY y las del Excel de parámetros de
  flujo de caja, sin "FALTA INGRESAR". DROPSHIPPING no existe como unidad.
- Categorías (76): unión del catálogo de wallets y "Conceptos de Gastos" del Excel, sin "FALTA INGRESAR" ni "PRUEBA"
  y sin duplicados, más "TRASLADO ENTRE WALLETS PROPIAS", que el motor propone para traslados entre wallets propias.
- Empresas: WIILOG, ASIATI, TIENDAS ASIATI, ORIGEN VITAL.
- Fijo/variable: FIJO, VARIABLE.

Las columnas Ciudad y Estado del Excel son de tesorería y no se cargan.
