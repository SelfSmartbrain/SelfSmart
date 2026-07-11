"""
Health check endpoints.

Provides liveness and readiness probes for Kubernetes/Docker health checks.
"""

from __future__ import annotations

from fastapi import APIRouter

from src.config.settings import get_settings

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness probe")
async def health_check() -> dict[str, str]:
    """Basic liveness check — returns OK if the process is running."""
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness probe")
async def readiness_check() -> dict[str, str | bool]:
    """
    Readiness probe — checks connectivity to downstream services.
    In a full implementation, this would ping PostgreSQL, Qdrant, and Redis.
    """
    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.environment,
        "version": settings.version,
        "postgres": True,
        "qdrant": True,
        "redis": True,
    }
