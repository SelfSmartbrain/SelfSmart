"""
Health check endpoints.

Provides liveness and readiness probes for Kubernetes/Docker health checks.
"""

from __future__ import annotations

import time
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.services import chat_runtime
from src.config.settings import get_settings
from src.db.session import get_session
from src.monitoring.health import get_system_health

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness probe")
async def health_check() -> dict:
    """Health check with LLM and RAG dependency status."""
    settings = get_settings()
    chromadb_status = "unknown"
    external_api_status = "unknown"
    mlx_status = "not_applicable" if not settings.use_local_llm else "unhealthy"

    try:
        if (
            hasattr(chat_runtime.rag_service, "knowledge_integrator")
            and chat_runtime.rag_service.knowledge_integrator is not None
        ):
            vector_store = chat_runtime.rag_service.knowledge_integrator.vector_store
            chromadb_status = "healthy" if vector_store is not None else "unhealthy"
        else:
            chromadb_status = "unhealthy"
    except Exception:
        chromadb_status = "unhealthy"

    if settings.use_local_llm:
        mlx_status = "healthy" if chat_runtime.local_llm_client is not None else "unhealthy"
        external_api_status = "not_applicable"
    else:
        external_api_status = (
            "healthy" if chat_runtime.llm_api_key_configured() else "unhealthy"
        )

    critical_healthy = (
        mlx_status == "healthy"
        if settings.use_local_llm
        else external_api_status == "healthy"
    )

    return {
        "status": "healthy" if critical_healthy else "degraded",
        "service": settings.app_name,
        "version": settings.app_version,
        "dependencies": {
            "chromadb": chromadb_status,
            "mlx": mlx_status,
            "external_api": external_api_status,
        },
    }


@router.get("/health/ready", summary="Readiness probe")
async def readiness_check(
    db_session: AsyncSession = Depends(get_session),
) -> dict:
    """Readiness probe — checks connectivity to downstream services."""
    settings = get_settings()
    health = await get_system_health(db_session)
    return {
        "status": health["status"],
        "environment": settings.environment,
        "version": settings.version,
        "services": health["services"],
    }


@router.get("/health/detailed", summary="Detailed health check")
async def health_detailed() -> dict:
    """Detailed component health — no sensitive paths or error details exposed."""
    settings = get_settings()
    components: dict = {}
    overall_status = "ok"

    try:
        if hasattr(chat_runtime.rag_service, "knowledge_integrator"):
            vi = chat_runtime.rag_service.knowledge_integrator.vector_store
            chunk_count = vi.collection.count() if vi else -1
        else:
            chunk_count = -1
        components["rag"] = {"status": "ok", "chunk_count": chunk_count}
    except Exception:
        components["rag"] = {"status": "error"}
        overall_status = "degraded"

    if chat_runtime.llm_api_key_configured():
        components["llm_api"] = {"status": "ok", "provider": settings.llm_provider}
    else:
        components["llm_api"] = {"status": "warning"}
        if overall_status == "ok":
            overall_status = "degraded"

    components["local_llm"] = {
        "status": "ok"
        if (chat_runtime.use_local_llm and chat_runtime.local_llm_client is not None)
        else "not_loaded",
        "enabled": chat_runtime.use_local_llm,
    }

    try:
        probe = settings.data_dir / ".health_probe"
        probe.touch()
        probe.unlink()
        components["storage"] = {"status": "ok"}
    except Exception:
        components["storage"] = {"status": "error"}
        overall_status = "error"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": round(time.time() - chat_runtime.SERVER_START_TIME, 1),
        "version": settings.app_version,
        "components": components,
    }
