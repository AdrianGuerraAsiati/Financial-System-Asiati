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

```bash
docker compose up --build
```

API:

```text
http://localhost:8000
```

Health check:

```text
GET /health
```

## Estado

Primer scaffold. Todavía no contiene las reglas reales de conciliación de wallets.
