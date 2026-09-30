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
