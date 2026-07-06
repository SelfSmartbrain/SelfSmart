"""
FastAPI Application Entry Point.

Configures the FastAPI application, lifespan events, middleware,
and mounts all route routers.
"""

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
    Initializes database connections, cache, and vector store on startup,
    and cleans them up on shutdown.
    """
    settings = get_settings()
    logger.info("Starting up autonomous agent platform", env=settings.environment)

    # Initialization logic would go here (e.g., connect to DBs)
    # This is handled mostly by dependency injection in routes,
    # but global singletons could be initialized here.

    yield

    logger.info("Shutting down autonomous agent platform")
    # Cleanup logic goes here


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
