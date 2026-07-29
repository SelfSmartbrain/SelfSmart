"""
Async database engine and session management with enhanced pooling.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    Pool,
    PoolProxiedConnection,
)
from sqlalchemy.pool import NullPool, QueuePool

from prometheus_client import Gauge, Histogram

from src.config.settings import get_settings
from src.config.logging import get_logger

logger = get_logger(__name__)

# Metrics
DB_POOL_SIZE = Gauge("db_pool_size", "Database connection pool size", ["database"])

DB_POOL_CHECKED_OUT = Gauge(
    "db_pool_checked_out", "Database connections currently checked out", ["database"]
)

DB_POOL_OVERFLOW = Gauge("db_pool_overflow", "Database pool overflow connections", ["database"])

DB_POOL_INVALID = Gauge("db_pool_invalid", "Database invalid connections in pool", ["database"])

DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds", "Database query duration", ["database", "operation"]
)


class MonitoredPool(QueuePool):
    """Connection pool with monitoring."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._database_name = "selfsmart"

    def status(self) -> dict:
        """Get pool status."""
        return {
            "size": self.size(),
            "checked_out": self.checkedout(),
            "overflow": self.overflow(),
            "invalid": self._invalidate_counter if hasattr(self, "_invalidate_counter") else 0,
        }

    def _do_get(self) -> PoolProxiedConnection:
        """Override to add monitoring."""
        conn = super()._do_get()
        self._update_metrics()
        return conn

    def _do_return_conn(self, conn: PoolProxiedConnection) -> None:
        """Override to add monitoring."""
        super()._do_return_conn(conn)
        self._update_metrics()

    def _update_metrics(self) -> None:
        """Update Prometheus metrics."""
        try:
            DB_POOL_SIZE.labels(database=self._database_name).set(self.size())
            DB_POOL_CHECKED_OUT.labels(database=self._database_name).set(self.checkedout())
            DB_POOL_OVERFLOW.labels(database=self._database_name).set(self.overflow())
        except Exception as e:
            logger.warning("failed_to_update_pool_metrics", error=str(e))


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Create and cache the async SQLAlchemy engine with enhanced pooling."""
    settings = get_settings()

    # Determine pool size based on environment
    if settings.is_production:
        pool_size = 20
        max_overflow = 30
    else:
        pool_size = 5
        max_overflow = 10

    logger.info(
        "creating_db_engine",
        pool_size=pool_size,
        max_overflow=max_overflow,
        database_url=settings.database_url[:50] + "...",
    )

    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_class=MonitoredPool,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,  # Recycle connections after 1 hour
        pool_timeout=30,  # Timeout for getting connection
        connect_args=(
            {
                "connect_timeout": 10,
                "command_timeout": 30,
            }
            if "postgresql" in settings.database_url
            else {}
        ),
    )


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create and cache the async session factory."""
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,  # Disable autoflush for explicit control
    )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def AsyncSessionLocal() -> AsyncSession:
    """Return a new ``AsyncSession`` context manager."""
    return get_session_factory()()


async def health_check() -> dict:
    """Check database health."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")

        pool = engine.pool
        if hasattr(pool, "status"):
            pool_status = pool.status()
        else:
            pool_status = {
                "size": pool.size(),
                "checked_out": pool.checkedout(),
            }

        return {
            "status": "healthy",
            "pool": pool_status,
        }
    except Exception as e:
        logger.error("db_health_check_failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
        }
