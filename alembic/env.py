"""
Alembic environment configuration with async SQLAlchemy support.

This module configures Alembic to:
- Use the application's ``Settings`` for the database URL.
- Run migrations in async mode via ``asyncpg``.
- Auto-detect schema changes against the ORM ``Base.metadata``.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.config.settings import get_settings

# Import Base so that metadata reflects all registered models.
from src.db.models import Base  # noqa: F401

# Alembic Config object — provides access to alembic.ini values.
config = context.config

# Configure Python logging from alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The MetaData object for 'autogenerate' support.
target_metadata = Base.metadata


def _get_url() -> str:
    """Resolve the database URL from application settings.

    For Alembic migrations we use the sync URL (psycopg2 driver).
    """
    settings = get_settings()
    return settings.database_url_sync


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This emits SQL to stdout rather than executing it against a live
    database. Useful for generating migration scripts for review.
    """
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations against a live database connection.

    Args:
        connection: A synchronous connection from the async engine.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using a sync engine.

    Creates a sync engine from the configuration and delegates to
    ``do_run_migrations``.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_url()

    from sqlalchemy import create_engine

    connectable = create_engine(
        configuration["sqlalchemy.url"],
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
