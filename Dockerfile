FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
RUN mkdir -p ./docs/motores/conciliacion_wallets ./docs/nucleo
COPY docs/motores/conciliacion_wallets/*.json ./docs/motores/conciliacion_wallets/
COPY docs/nucleo/dimensiones_iniciales.json ./docs/nucleo/

# Preferir ruedas binarias: SQLAlchemy desde sdist se compila durante horas
# en Lightsail micro (1 GB de RAM). Fallar rápido si no existe wheel compatible.
RUN python -m pip install --disable-pip-version-check --no-cache-dir \
    --only-binary=:all: "SQLAlchemy>=2.0,<3.0" \
    && python -m pip install --disable-pip-version-check --no-cache-dir --prefer-binary .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]