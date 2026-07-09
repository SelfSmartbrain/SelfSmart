"""
Async database engine and session management.

Provides:
- ``get_engine()``: cached async engine with connection pooling.
- ``get_session_factory()``: cached ``async_sessionmaker`` bound to the engine.
- ``get_session()``: FastAPI dependency that yields an ``AsyncSession``.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config.settings import get_settings


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Create and cache the async SQLAlchemy engine.

    Uses ``asyncpg`` as the driver with sensible pool defaults for a
    production workload.

    Returns:
        The singleton ``AsyncEngine`` instance.
    """
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=300,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create and cache the async session factory.

    Returns:
        A configured ``async_sessionmaker`` bound to the engine.
    """
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    The session is automatically committed on success and rolled back
    on exception. It is always closed after use.

    Yields:
        An ``AsyncSession`` for the request lifecycle.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def AsyncSessionLocal() -> AsyncSession:
    """Return a new ``AsyncSession`` context manager.

    Designed for use outside of FastAPI's DI (e.g. background tasks,
    the DB-watcher in lifespan, the evolution benchmark workers).

    Usage::

        async with AsyncSessionLocal() as session:
            ...

    Returns:
        An ``AsyncSession`` context-manager object.
    """
    return get_session_factory()()
