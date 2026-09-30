from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.db import Base
from app.core import cargas, empresas, fuentes, hallazgos, periodos  # noqa: F401
from app.core.periodos import history as periodos_history  # noqa: F401
from app.core import auditoria, usuarios  # noqa: F401
from app.core.auth import model as auth_model  # noqa: F401
from app.motores.compras_supply_chain import model as compras_model  # noqa: F401
from app.motores.cartera_ocs import snapshot_model as cartera_snapshot_model  # noqa: F401
from app.integrations.google_sheets import model as google_sheets_model  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
