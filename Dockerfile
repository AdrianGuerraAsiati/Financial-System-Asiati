FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
RUN mkdir -p ./docs/motores/conciliacion_wallets ./docs/nucleo
COPY docs/motores/conciliacion_wallets/*.json ./docs/motores/conciliacion_wallets/
COPY docs/nucleo/dimensiones_iniciales.json ./docs/nucleo/

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]