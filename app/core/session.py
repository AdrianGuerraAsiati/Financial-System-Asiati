import os
from contextlib import contextmanager
from functools import lru_cache
from collections.abc import Generator, Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@lru_cache(maxsize=4)
def _session_factory(database_url: str) -> sessionmaker[Session]:
    engine = create_engine(database_url)
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def crear_session() -> Iterator[Session]:
    """Crea una sesión reutilizable fuera del ciclo de dependencias de FastAPI."""
    database_url = os.environ["DATABASE_URL"]
    factory = _session_factory(database_url)
    with factory() as session:
        yield session


def obtener_session() -> Generator[Session, None, None]:
    """Entrega una sesión de base de datos usando la URL configurada por entorno."""
    with crear_session() as session:
        yield session
