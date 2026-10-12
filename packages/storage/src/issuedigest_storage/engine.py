"""Explicit PostgreSQL connections with sanitized configuration failures."""

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError


def verify_engine(engine: Engine) -> None:
    if engine.dialect.name != "postgresql" or engine.dialect.driver != "psycopg":
        raise ValueError("Storage requires PostgreSQL with psycopg")
    try:
        with engine.connect() as connection:
            version = connection.scalar(text("SELECT version()"))
            if not isinstance(version, str) or not version.startswith("PostgreSQL "):
                raise ValueError("Storage requires a PostgreSQL server")
    except (SQLAlchemyError, ValueError):
        raise ValueError("Unable to verify PostgreSQL storage connection") from None


def create_storage_engine(database_url: str) -> Engine:
    """Connect and verify the server; never initialize or migrate its schema."""
    try:
        url = make_url(database_url)
    except (SQLAlchemyError, ValueError, TypeError):
        raise ValueError("Invalid storage connection configuration") from None
    if url.drivername != "postgresql+psycopg":
        raise ValueError("Storage requires a postgresql+psycopg URL")
    engine: Engine | None = None
    try:
        engine = create_engine(url, hide_parameters=True, echo=False, pool_pre_ping=True)
        verify_engine(engine)
    except (SQLAlchemyError, ValueError, TypeError):
        if engine is not None:
            engine.dispose()
        raise ValueError("Unable to connect to PostgreSQL storage") from None
    return engine
