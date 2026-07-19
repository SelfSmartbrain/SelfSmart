"""
Retry mechanism with exponential backoff and jitter.
"""

import asyncio
import random
import time
from typing import Callable, TypeVar, Optional, Type
from functools import wraps

from prometheus_client import Counter, Histogram

from src.config.logging import get_logger

logger = get_logger(__name__)

# Metrics
RETRY_ATTEMPTS = Counter(
    "retry_attempts_total",
    "Total retry attempts",
    ["function", "outcome"]
)

RETRY_DURATION = Histogram(
    "retry_duration_seconds",
    "Retry operation duration",
    ["function"]
)


T = TypeVar('T')


class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[tuple[Type[Exception], ...]] = None
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or (
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
        )


async def retry_with_backoff(
    func: Callable[..., T],
    config: Optional[RetryConfig] = None,
    function_name: Optional[str] = None
) -> T:
    """
    Execute function with retry and exponential backoff.
    
    Args:
        func: Function to execute
        config: Retry configuration
        function_name: Name for metrics (defaults to func.__name__)
    
    Returns:
        Function result
    
    Raises:
        Exception: Last exception if all retries exhausted
    """
    config = config or RetryConfig()
    func_name = function_name or func.__name__
    
    last_exception = None
    start_time = time.time()
    
    for attempt in range(config.max_attempts):
        try:
            result = await func()
            
            # Record success
            duration = time.time() - start_time
            RETRY_DURATION.labels(function=func_name).observe(duration)
            RETRY_ATTEMPTS.labels(
                function=func_name,
                outcome="success"
            ).inc(attempt + 1)
            
            return result
            
        except Exception as e:
            last_exception = e
            
            # Check if exception is retryable
            if config.retryable_exceptions and not isinstance(
                e, config.retryable_exceptions
            ):
                RETRY_ATTEMPTS.labels(
                    function=func_name,
                    outcome="non_retryable"
                ).inc()
                raise
            
            # Log retry
            logger.warning(
                "retry_attempt",
                function=func_name,
                attempt=attempt + 1,
                max_attempts=config.max_attempts,
                error=str(e)
            )
            
            # Calculate delay with exponential backoff and jitter
            if attempt < config.max_attempts - 1:
                delay = min(
                    config.base_delay * (config.exponential_base ** attempt),
                    config.max_delay
                )
                
                if config.jitter:
                    delay = delay * (0.5 + random.random() * 0.5)
                
                await asyncio.sleep(delay)
    
    # All retries exhausted
    RETRY_ATTEMPTS.labels(
        function=func_name,
        outcome="exhausted"
    ).inc(config.max_attempts)
    
    raise last_exception or Exception("Retry exhausted")


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[tuple[Type[Exception], ...]] = None
):
    """Decorator to apply retry logic to async function."""
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions
    )
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_with_backoff(
                lambda: func(*args, **kwargs),
                config,
                func.__name__
            )
        return wrapper
    return decorator