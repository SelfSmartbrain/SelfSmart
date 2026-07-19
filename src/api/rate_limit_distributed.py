"""
Distributed rate limiting using Redis with tiered access levels.
Supports IP-based, user-based, and API key-based limiting with sliding windows.
"""

import json
import time
from typing import Optional, Union
from dataclasses import dataclass
from enum import Enum

import redis.asyncio as redis
from fastapi import Request, HTTPException, status
from prometheus_client import Counter

from src.config.settings import get_settings
from src.config.logging import get_logger

logger = get_logger(__name__)

# Metrics
RATE_LIMIT_REQUESTS = Counter(
    "rate_limit_requests_total",
    "Total rate limit checks",
    ["limit_type", "result"]
)

RATE_LIMIT_CURRENT = Counter(
    "rate_limit_current_usage",
    "Current rate limit usage",
    ["limit_type", "key"]
)


class RateLimitTier(Enum):
    """User access tiers with different rate limits."""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class RateLimitConfig:
    """Rate limit configuration for a specific tier."""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_allowance: int = 10


# Tier configurations
TIER_CONFIGS = {
    RateLimitTier.FREE: RateLimitConfig(
        requests_per_minute=20,
        requests_per_hour=500,
        requests_per_day=2000,
        burst_allowance=5
    ),
    RateLimitTier.BASIC: RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1500,
        requests_per_day=10000,
        burst_allowance=20
    ),
    RateLimitTier.PRO: RateLimitConfig(
        requests_per_minute=200,
        requests_per_hour=5000,
        requests_per_day=50000,
        burst_allowance=50
    ),
    RateLimitTier.ENTERPRISE: RateLimitConfig(
        requests_per_minute=1000,
        requests_per_hour=20000,
        requests_per_day=200000,
        burst_allowance=200
    ),
}

# Endpoint-specific overrides (more restrictive for expensive operations)
ENDPOINT_OVERRIDES = {
    "/api/auth/login": RateLimitConfig(
        requests_per_minute=5,
        requests_per_hour=20,
        requests_per_day=50,
        burst_allowance=2
    ),
    "/api/auth/register": RateLimitConfig(
        requests_per_minute=3,
        requests_per_hour=10,
        requests_per_day=30,
        burst_allowance=2
    ),
    "/api/chat": RateLimitConfig(
        requests_per_minute=30,
        requests_per_hour=1000,
        requests_per_day=5000,
        burst_allowance=10
    ),
}


class DistributedRateLimiter:
    """Redis-backed distributed rate limiter with sliding window."""
    
    def __init__(self):
        self.settings = get_settings()
        self._redis: Optional[redis.Redis] = None
        self._prefix = "ratelimit"
    
    async def get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
        return self._redis
    
    async def check_rate_limit(
        self,
        key: str,
        config: RateLimitConfig,
        window: str = "minute"
    ) -> tuple[bool, dict]:
        """
        Check if request is within rate limits using sliding window.
        
        Args:
            key: Unique identifier (IP, user ID, API key)
            config: Rate limit configuration
            window: Time window ('minute', 'hour', 'day')
        
        Returns:
            (allowed, info): Whether request is allowed and usage info
        """
        redis_client = await self.get_redis()
        
        # Determine window parameters
        window_seconds = {
            "minute": 60,
            "hour": 3600,
            "day": 86400
        }[window]
        
        limit = {
            "minute": config.requests_per_minute,
            "hour": config.requests_per_hour,
            "day": config.requests_per_day
        }[window]
        
        # Redis key for this window
        redis_key = f"{self._prefix}:{key}:{window}"
        
        # Current timestamp
        now = time.time()
        window_start = now - window_seconds
        
        # Use sorted set for sliding window
        pipe = redis_client.pipeline()
        
        # Remove entries outside the window
        pipe.zremrangebyscore(redis_key, 0, window_start)
        
        # Count current requests in window
        pipe.zcard(redis_key)
        
        # Add current request
        pipe.zadd(redis_key, {str(now): now})
        
        # Set expiration
        pipe.expire(redis_key, window_seconds + 60)
        
        results = await pipe.execute()
        current_count = results[1]
        
        # Check if limit exceeded
        allowed = current_count <= limit
        
        # Calculate reset time
        oldest_entry = await redis_client.zrange(redis_key, 0, 0, withscores=True)
        reset_time = oldest_entry[0][1] + window_seconds if oldest_entry else now + window_seconds
        
        info = {
            "limit": limit,
            "remaining": max(0, limit - current_count),
            "reset": int(reset_time),
            "current": current_count,
            "window": window
        }
        
        # Update metrics
        RATE_LIMIT_REQUESTS.labels(
            limit_type=window,
            result="allowed" if allowed else "denied"
        ).inc()
        
        if allowed:
            RATE_LIMIT_CURRENT.labels(
                limit_type=window,
                key=key[:20]  # Truncate for cardinality
            ).inc()
        
        return allowed, info
    
    async def get_user_tier(self, user_id: str) -> RateLimitTier:
        """Get user's rate limit tier from database."""
        # TODO: Implement database lookup
        # For now, default to FREE tier
        return RateLimitTier.FREE
    
    async def check_request(
        self,
        request: Request,
        user_id: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> tuple[bool, dict]:
        """
        Check rate limits for a request.
        
        Checks multiple limits in order: minute, hour, day.
        Uses the most restrictive limit that applies.
        """
        # Determine the key to use for rate limiting
        if user_id:
            key = f"user:{user_id}"
            tier = await self.get_user_tier(user_id)
        elif api_key:
            key = f"apikey:{api_key}"
            tier = RateLimitTier.ENTERPRISE  # API keys get enterprise tier
        else:
            # Fall back to IP-based limiting
            client_ip = self._get_client_ip(request)
            key = f"ip:{client_ip}"
            tier = RateLimitTier.FREE
        
        # Get base config for tier
        config = TIER_CONFIGS[tier]
        
        # Check for endpoint-specific overrides
        path = request.url.path
        if path in ENDPOINT_OVERRIDES:
            config = ENDPOINT_OVERRIDES[path]
        
        # Check all windows
        for window in ["minute", "hour", "day"]:
            allowed, info = await self.check_rate_limit(key, config, window)
            if not allowed:
                logger.warning(
                    "rate_limit_exceeded",
                    key=key,
                    window=window,
                    current=info["current"],
                    limit=info["limit"]
                )
                return False, info
        
        return True, {"tier": tier.value}
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxies."""
        # Check for forwarded headers
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # X-Forwarded-For can contain multiple IPs, take the first
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection
        if request.client:
            return request.client.host
        
        return "unknown"


# Global limiter instance
limiter = DistributedRateLimiter()


async def check_rate_limit_dependency(
    request: Request,
    user_id: Optional[str] = None,
    api_key: Optional[str] = None
) -> None:
    """FastAPI dependency for rate limiting."""
    allowed, info = await limiter.check_request(request, user_id, api_key)
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "limit": info["limit"],
                "remaining": info["remaining"],
                "reset": info["reset"],
                "window": info["window"]
            },
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": str(info["remaining"]),
                "X-RateLimit-Reset": str(info["reset"]),
                "Retry-After": str(int(info["reset"] - time.time()))
            }
        )