# Financial System ASIATI

Plataforma financiera de ASIATI construida como un **núcleo compartido + motores independientes**.

## Primer objetivo

Poner en producción el **Motor 01: Conciliación de Wallets** antes de construir los demás motores.

El núcleo inicial será deliberadamente mínimo. La interfaz común se considera **provisional hasta construir el segundo motor**, porque la arquitectura del proyecto indica que la abstracción real debe extraerse a partir de casos concretos y no diseñarse completa por anticipado.

## Estructura inicial

```text
app/
├── main.py
├── core/
│   └── motor.py
└── motores/
    └── conciliacion_wallets/
        └── engine.py
tests/
└── test_wallet_engine_contract.py
```

## Stack inicial

- Python
- FastAPI
- PostgreSQL
- Docker
- pytest

## Principios

1. Un solo sistema para múltiples empresas; la empresa es configuración, no una copia del código.
2. Un solo PostgreSQL; no microservicios ni una base por línea de negocio.
3. El core contiene únicamente capacidades realmente compartidas.
4. Cada motor conserva sus reglas y tablas propias mientras no exista evidencia de que deben subir al core.
5. Cada archivo cargado deberá terminar soportando trazabilidad, integridad e idempotencia.
6. El Motor 01 debe validarse contra casos reales antes de considerarse correcto.

## Motores previstos

- conciliacion_wallets
- conciliacion_bancos
- cartera_ocs
- recaudos_ultima_milla
- conciliacion_chin_chin
- flujo_caja

Los cinco primeros son motores de conciliación. `flujo_caja` será un motor de reporte que lee la información categorizada generada por la plataforma.

## Desarrollo local

Arranque rápido:

```bash
docker compose up --build
```

El compose de desarrollo ejecuta automáticamente las migraciones, crea una empresa local y asegura un superadministrador.

Abre:

```text
http://localhost:8000
```

Credenciales locales por defecto:

```text
admin@asiati.local
AsiatiDev2026!
```

Compras / Supply Chain usa datos sintéticos claramente marcados como **DEMO LOCAL** hasta que conectes Google Sheets.

Guía completa, conexión al Sheet real y reset local:

`DEV_SETUP.md`

Health check:

```text
GET /health
```

## Estado

La plataforma ya incluye núcleo de autenticación/autorización, Cartera, conciliación Wiilog y un vertical read-only de Compras / Supply Chain con explorador, diagnóstico de fuente y familias monetarias de costo y DDP.
