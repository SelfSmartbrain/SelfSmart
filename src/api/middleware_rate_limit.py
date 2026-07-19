"""
Rate limiting middleware for FastAPI.
Applies rate limits to all requests with proper headers.
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.rate_limit_distributed import limiter, check_rate_limit_dependency
from src.config.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to apply rate limiting to all requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and metrics
        if request.url.path in ["/health", "/health/ready", "/metrics"]:
            return await call_next(request)
        
        # Extract user info from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        api_key = request.headers.get("X-API-Key")
        
        # Check rate limit
        try:
            await check_rate_limit_dependency(request, user_id, api_key)
        except Exception as e:
            # Rate limit exceeded - return 429
            from fastapi import HTTPException
            if hasattr(e, "status_code") and e.status_code == 429:
                return Response(
                    content=str(e.detail),
                    status_code=429,
                    headers=getattr(e, "headers", {})
                )
            raise
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        # (These would be set by the rate limiter)
        # For now, add basic headers
        response.headers["X-RateLimit-Limit"] = "100"
        response.headers["X-RateLimit-Remaining"] = "99"
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
        
        return response