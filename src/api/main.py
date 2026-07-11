"""
FastAPI Application Entry Point.

Configures the FastAPI application, lifespan events, middleware,
and mounts all route routers.
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.api.middleware import setup_middleware
from src.api.routes import (
    autonomous,
    benchmarks,
    cognition,
    environment,
    failures,
    goals,
    health,
    impact,
    knowledge,
    memory,
    meta,
    opportunities,
    programs,
    reflections,
    reports,
    review,
    skills,
    strategies,
    swarm,
    tasks,
    tools,
    vision,
    world_model,
)
from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifecycle.
    Initializes the AgentRuntime, EvolutionEngine, and a DB-watcher background
    task on startup, and cleans them all up on shutdown.
    """
    settings = get_settings()
    logger.info("Starting up autonomous agent platform", env=settings.environment)

    # ── Initialize the runtime ──────────────────────────────────────────────
    from src.runtime.runtime_singleton import init_runtime, shutdown_runtime
    runtime = await init_runtime()

    # ── Start EvolutionEngine (optional — skip gracefully if misconfigured) ──
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
        logger.warning("EvolutionEngine failed to start; continuing without evolution", error=str(exc))
        evolution_engine = None

    # ── Background task: sync DB objectives → ObjectiveManager every 10 s ──
    async def _db_watcher() -> None:
        """Poll PostgreSQL for ACTIVE objectives and push them into the runtime."""
        from sqlalchemy import select

        from src.autonomy.objective_manager import Objective
        from src.db.enums import ObjectiveStatus
        from src.db.models import Objective as ObjectiveModel
        from src.db.session import AsyncSessionLocal  # proper sessionmaker, not a generator

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
                            runtime.objective_manager.set_objective(
                                Objective.from_db_model(db_obj)
                            )
                            seen.add(db_obj.objective_id)
                            logger.info(
                                "Loaded objective from DB", id=db_obj.objective_id
                            )
            except asyncio.CancelledError:
                raise  # propagate cancellation immediately
            except Exception as exc:
                logger.error("DB watcher error", error=str(exc))
            await asyncio.sleep(10)

    watcher_task = asyncio.create_task(_db_watcher(), name="db-objective-watcher")
    # Run the execution loop as a long-lived background task (fire-and-forget).
    # We do NOT await its result here because run() blocks until stopped.
    loop_task = asyncio.create_task(runtime.run(), name="agent-execution-loop")

    yield

    # ── Cleanup — cancel tasks and await them to avoid ResourceWarning ──────
    logger.info("Shutting down autonomous agent platform")
    for task in (watcher_task, loop_task):
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass  # expected on cancellation

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
        description="Phase 1 AGI-Inspired Autonomous Agent Platform",
        version=settings.version,
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
    )

    # Setup middleware (CORS, logging, error handling)
    setup_middleware(app, settings)

    # Include routers
    from src.api.routes import auth_routes

    app.include_router(auth_routes.router, prefix="/api/v1/auth", tags=["Auth"])
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

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Catch-all exception handler to prevent leaking sensitive info."""
        logger.error("Unhandled exception", path=request.url.path, error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Please try again later."},
        )

    return app


app = create_app()
