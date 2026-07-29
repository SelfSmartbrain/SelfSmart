"""
FastAPI Application Entry Point.

Configures the FastAPI application, lifespan events, middleware,
and mounts all route routers.
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware import setup_middleware
from src.api.middleware_rate_limit import RateLimitMiddleware
from src.api.middleware_security import (
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
    TimeoutMiddleware,
)
from src.api.routes import (
    autonomous,
    benchmarks,
    chat,
    cognition,
    conversations,
    environment,
    failures,
    feedback,
    goals,
    health,
    impact,
    knowledge,
    learning,
    legacy_auth,
    memory,
    meta,
    opportunities,
    programs,
    reflections,
    reports,
    review,
    skills,
    stats,
    strategies,
    swarm,
    tasks,
    tools,
    vision,
    world_model,
)
from src.api.services import chat_runtime
from src.config.logging import get_logger, setup_logging
from src.config.settings import get_settings
from src.monitoring.prometheus import setup_prometheus

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifecycle.
    Initializes the AgentRuntime, EvolutionEngine, chat runtime, and a DB-watcher
    background task on startup, and cleans them all up on shutdown.
    """
    settings = get_settings()
    setup_logging(
        level="DEBUG" if settings.debug else "INFO",
        json_format=settings.json_logs,
    )
    logger.info("Starting up autonomous agent platform", env=settings.environment)

    await chat_runtime.prewarm_local_llm()

    from src.runtime.runtime_singleton import init_runtime, shutdown_runtime

    runtime = await init_runtime()

    evolution_engine = None
    try:
        from src.evolution.evolution_engine import EvolutionConfig, EvolutionEngine

        evolution_engine = EvolutionEngine(
            config=EvolutionConfig(
                generation_limit=100,
                population_size=20,
                mutation_rate=0.1,
                parallel_benchmark_workers=2,
            )
        )
        await evolution_engine.start()
        logger.info("EvolutionEngine started")
    except Exception as exc:
        logger.warning(
            "EvolutionEngine failed to start; continuing without evolution", error=str(exc)
        )
        evolution_engine = None

    async def _db_watcher() -> None:
        from sqlalchemy import select

        from src.autonomy.objective_manager import Objective
        from src.db.enums import ObjectiveStatus
        from src.db.models import Objective as ObjectiveModel
        from src.db.session import AsyncSessionLocal

        seen: set[str] = set()
        while True:
            try:
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(ObjectiveModel).where(
                            ObjectiveModel.status == ObjectiveStatus.ACTIVE
                        )
                    )
                    for db_obj in result.scalars().all():
                        if db_obj.objective_id not in seen:
                            runtime.objective_manager.set_objective(Objective.from_db_model(db_obj))
                            seen.add(db_obj.objective_id)
                            logger.info("Loaded objective from DB", id=db_obj.objective_id)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("DB watcher error", error=str(exc))
            await asyncio.sleep(10)

    watcher_task = asyncio.create_task(_db_watcher(), name="db-objective-watcher")
    loop_task = asyncio.create_task(runtime.run(), name="agent-execution-loop")

    yield

    logger.info("Shutting down autonomous agent platform")
    for task in (watcher_task, loop_task):
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    if evolution_engine is not None:
        try:
            await evolution_engine.stop()
        except Exception as exc:
            logger.warning("EvolutionEngine stop error", error=str(exc))

    await shutdown_runtime()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.project_name,
        description="SelfSmart AI — Intelligent Self-Learning Chatbot & Agent Platform",
        version=settings.version,
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
    )

    # Remove old slowapi middleware
    # app.state.limiter = limiter
    # app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    # app.add_middleware(SlowAPIMiddleware)

    # Add new distributed rate limiting middleware
    setup_middleware(app, settings)
    setup_prometheus(app)

    # Add security middleware (should be added early)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware, max_size=10 * 1024 * 1024)
    app.add_middleware(TimeoutMiddleware, timeout=60.0)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Add rate limiting middleware after CORS
    app.add_middleware(RateLimitMiddleware)

    from src.api.routes import auth_routes

    # SelfSmart chat frontend routes (/api/*)
    app.include_router(legacy_auth.router)
    app.include_router(chat.router)
    app.include_router(conversations.router)
    app.include_router(feedback.router)
    app.include_router(learning.router)
    app.include_router(stats.router)

    # Autonomous agent platform routes (/api/v1/*)
    app.include_router(auth_routes.router, prefix="/api/v1/auth", tags=["Auth v1"])
    app.include_router(health.router)
    app.include_router(goals.router, prefix="/api/v1/goals", tags=["Goals"])
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
    app.include_router(memory.router, prefix="/api/v1/memory", tags=["Memory"])
    app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["Knowledge"])
    app.include_router(reflections.router, prefix="/api/v1/reflections", tags=["Reflections"])
    app.include_router(meta.router, prefix="/api/v1/meta", tags=["Meta-Learning"])
    versioned_routers = (
        autonomous.router,
        benchmarks.router,
        cognition.router,
        environment.router,
        failures.router,
        impact.router,
        opportunities.router,
        programs.router,
        reports.router,
        review.router,
        skills.router,
        strategies.router,
        swarm.router,
        tools.router,
        vision.router,
        world_model.router,
    )
    for router in versioned_routers:
        app.include_router(router, prefix="/api/v1")

    @app.get("/")
    async def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "online",
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/status")
    async def status():
        return {
            "status": "online",
            "app_name": settings.app_name,
            "version": settings.app_version,
            "debug": settings.debug,
            "llm_provider": settings.llm_provider,
            "llm_api_key_configured": chat_runtime.llm_api_key_configured(),
            "embeddings": "sentence-transformers",
            "features": [
                "rag",
                "continuous_learning",
                "streaming_chat",
                "feedback",
                "conversation_history",
            ],
        }

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("unhandled_exception", path=request.url.path, error=str(exc), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Please try again later."},
        )

    return app


app = create_app()
