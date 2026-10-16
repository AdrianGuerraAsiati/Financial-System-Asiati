# Baseline privado de regresión · Wallet Wiilog

Los datos y valores esperados de un cierre real **no se versionan**.

Para ejecutar `tests/wallet_wiilog/test_regresion_septiembre.py`, el entorno local
debe aportar:

```
fixtures/wallet_wiilog/2026-09/
├── ordenes_<export>.xlsx
├── historyWallet_<export>.xlsx
└── expected_baseline.json
```

`fixtures/` está ignorado por Git.

## Contrato de expected_baseline.json

El archivo privado debe tener esta forma. Los marcadores describen el tipo de dato;
no son valores de negocio:

```json
{
  "periodo_inicio": "<YYYY-MM-DD>",
  "periodo_fin": "<YYYY-MM-DD>",
  "wallet_principal_email": "<identificador operativo>",
  "c0": {
    "estado": "<estado esperado>",
    "detalle": {
      "saldo_inicial": "<decimal>",
      "entradas": "<decimal>",
      "salidas": "<decimal>",
      "saldo_final": "<decimal>",
      "quiebres": 0
    }
  },
  "ordenes_agrupadas": 0,
  "ff_por_estado": {},
  "ff_monto_en_juego_c": {},
  "ff_no_cobrado_por_bodega": {},
  "ff_fuera": {},
  "flete_por_estado": {},
  "flete_fuera": 0,
  "movimientos": {
    "por_revisar": 0,
    "cruces": 0,
    "sin_concepto": 0
  }
}
```

Los valores reales deben provenir del cierre validado y conservarse en almacenamiento
privado. Si una regla de negocio cambia de forma aprobada, el baseline privado se
actualiza junto con la evidencia de esa decisión; no se copian las cifras al repositorio.

## Línea base privada de Recompra Menpros (quinta wallet)

La suite `tests/wallet_tiendas/test_regresion_recompra_septiembre.py`
requiere **dos archivos privados** bajo `fixtures/wallet_tiendas/2026-09/`:

- `wallet_recompra_menpros_<export>.xlsx`: un solo archivo de movimientos.
- `expected_recompra_menpros.json`: valores esperados de una conciliación **ya validada** por negocio.

También necesita exactamente un `ordenes_*.xlsx` en
`fixtures/wallet_wiilog/2026-09/`, correspondiente al mismo reporte
de septiembre de las demás tiendas. El identificador Wiilog se configura
en el entorno sin copiarlo al JSON.

Contrato del JSON **sin valores financieros reales**:

```json
{
  "periodo_inicio": "<YYYY-MM-DD>",
  "periodo_fin": "<YYYY-MM-DD>",
  "corte_ordenes": "<YYYY-MM-DD HH:MM>",
  "c0": {
    "estado": "<estado aprobado>",
    "detalle": {
      "saldo_inicial": "<decimal>",
      "entradas": "<decimal>",
      "salidas": "<decimal>",
      "saldo_final": "<decimal>",
      "quiebres": "<entero>"
    }
  },
  "movimientos": {
    "total": "<entero>",
    "requiere_revision": "<entero>",
    "sin_concepto": "<entero>"
  },
  "ganancia_por_estado": {},
  "hallazgos_por_gravedad": {}
}
```

Los campos entre corchetes angulares son **marcadores de esquema**: al
completar el archivo privado, los conteos deben ser enteros reales y las
medidas de saldo deben seguir el formato exacto producido por el motor.
Los dos diccionarios de distribución deben contener los recuentos reales
aprobados; `{}` solo si la distribución aprobada está vacía.

**Prohibido generar el esperado a partir de la misma corrida que se valida.**
No copiar saldos, identificadores, rutas de S3, datos de origen ni salidas
de pytest con diferencias operativas al repositorio o a una issue pública.

## Gate estricto del Bloque 1

Desde la raíz de un checkout en un equipo autorizado:

```bash
python ops/validar_regresion_privada_wallets.py
```

Se ejecutan las tres suites privadas que abarcan las cinco wallets. La
ausencia de fixtures, valores esperados, configuración o cualquier fallo
de cálculo impide el PASS del gate. Este resultado no reemplaza la prueba
funcional UI y la aprobación del área financiera.
