"""
API Middleware Configuration.

Sets up CORS, request logging, and rate limiting middleware.
"""

import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.logging import get_logger
from src.config.settings import Settings

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and their execution time."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        process_time_ms = (time.time() - start_time) * 1000
        
        # Log request details
        logger.info(
            "API Request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=int(process_time_ms),
            client=request.client.host if request.client else "unknown"
        )
        
        return response


def setup_middleware(app: FastAPI, settings: Settings) -> None:
    """Register all middleware for the FastAPI application."""
    
    # 1. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 2. Request Logging Middleware
    app.add_middleware(RequestLoggingMiddleware)
    
    # Note: Rate limiting middleware would typically be added here,
    # often using a library like slowapi or a custom Redis-backed middleware.
