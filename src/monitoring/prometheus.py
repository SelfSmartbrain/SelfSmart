"""
src/monitoring/prometheus.py

Purpose:
Provides Prometheus metrics exposition and middleware for FastAPI.
Tracks request duration, active requests, and custom cognitive metrics.
"""

from __future__ import annotations

import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app

# Standard HTTP metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"]
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"]
)

ACTIVE_REQUESTS = Gauge(
    "active_requests",
    "Number of currently active requests",
    ["method", "endpoint"]
)

# Cognitive Agent Metrics (Phase 7.5 Integration)
AGENT_TASKS_COMPLETED = Counter(
    "agent_tasks_completed_total",
    "Total number of tasks completed by agents",
    ["agent_type", "status"]
)

SYSTEM_AUTONOMY_SCORE = Gauge(
    "system_autonomy_score",
    "Current overall autonomy score of the system"
)

LEARNING_VELOCITY = Gauge(
    "learning_velocity",
    "Rate of new knowledge/skill acquisition"
)

# Phase 17: Runtime Metrics
OBJECTIVE_COMPLETION_RATE = Gauge(
    "objective_completion_rate",
    "Rate of objectives successfully completed"
)

OBJECTIVE_FAILURE_RATE = Gauge(
    "objective_failure_rate",
    "Rate of objectives that failed"
)

RUNTIME_UTILIZATION = Gauge(
    "runtime_utilization",
    "Current runtime utilization (0.0 to 1.0)"
)

AVERAGE_CYCLE_TIME = Gauge(
    "average_cycle_time_seconds",
    "Average time to complete an objective cycle"
)

ACTIVE_OBJECTIVES = Gauge(
    "active_objectives",
    "Number of currently active objectives"
)


def setup_prometheus(app: FastAPI) -> None:
    """Mount Prometheus metrics endpoint on the FastAPI app."""
    # Mount the /metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    @app.middleware("http")
    async def prometheus_middleware(request: Request, call_next: Callable) -> Response:
        """Middleware to track standard HTTP metrics."""
        method = request.method
        # Extract path without query params, default to unknown if absent
        endpoint = request.url.path if request.url else "unknown"
        
        # We don't want to track high cardinality routes unnecessarily,
        # but for internal apps, path is usually fine.
        
        ACTIVE_REQUESTS.labels(method=method, endpoint=endpoint).inc()
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as e:
            status_code = 500
            raise e
        finally:
            duration = time.time() - start_time
            ACTIVE_REQUESTS.labels(method=method, endpoint=endpoint).dec()
            HTTP_REQUESTS_TOTAL.labels(
                method=method, 
                endpoint=endpoint, 
                status_code=status_code
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method, 
                endpoint=endpoint
            ).observe(duration)
