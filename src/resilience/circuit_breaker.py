"""
Circuit breaker implementation for external service calls.
Prevents cascading failures and provides fallback mechanisms.
"""

import asyncio
import time
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Callable, Optional, Any, TypeVar
from functools import wraps
from collections import deque

from prometheus_client import Counter, Gauge, Histogram

from src.config.logging import get_logger

logger = get_logger(__name__)

# Metrics
CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_state",
    "Current circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["service"],
)

CIRCUIT_BREAKER_FAILURES = Counter(
    "circuit_breaker_failures_total", "Total circuit breaker failures", ["service"]
)

CIRCUIT_BREAKER_SUCCESSES = Counter(
    "circuit_breaker_successes_total", "Total circuit breaker successes", ["service"]
)

CIRCUIT_BREAKER_CALLS = Histogram(
    "circuit_breaker_call_duration_seconds", "Circuit breaker call duration", ["service"]
)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = auto()  # Normal operation
    OPEN = auto()  # Circuit is open, calls fail fast
    HALF_OPEN = auto()  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes to close circuit
    timeout: float = 60.0  # Seconds before trying half-open
    call_timeout: float = 30.0  # Timeout for individual calls
    max_retries: int = 3  # Max retry attempts
    retry_delay: float = 1.0  # Delay between retries


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker."""

    failures: int = 0
    successes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    recent_failures: deque = field(default_factory=lambda: deque(maxlen=100))


T = TypeVar("T")


class CircuitBreaker:
    """Circuit breaker implementation."""

    def __init__(self, service_name: str, config: Optional[CircuitBreakerConfig] = None):
        self.service_name = service_name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function through the circuit breaker.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: If function fails after retries
        """
        async with self._lock:
            # Check if circuit is open
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    logger.info("circuit_breaker_half_open", service=self.service_name)
                else:
                    CIRCUIT_BREAKER_STATE.labels(service=self.service_name).set(1)
                    raise CircuitBreakerOpenError(f"Circuit breaker open for {self.service_name}")

            # Update metrics
            CIRCUIT_BREAKER_STATE.labels(service=self.service_name).set(
                0 if self.state == CircuitState.CLOSED else 2
            )

        # Execute with retries
        last_exception = None
        for attempt in range(self.config.max_retries):
            try:
                start_time = time.time()

                # Execute with timeout
                result = await asyncio.wait_for(
                    func(*args, **kwargs), timeout=self.config.call_timeout
                )

                duration = time.time() - start_time
                CIRCUIT_BREAKER_CALLS.labels(service=self.service_name).observe(duration)

                # Record success
                async with self._lock:
                    self._on_success()

                return result

            except asyncio.TimeoutError as e:
                last_exception = e
                logger.warning(
                    "circuit_breaker_timeout", service=self.service_name, attempt=attempt + 1
                )
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)

            except Exception as e:
                last_exception = e
                logger.warning(
                    "circuit_breaker_failure",
                    service=self.service_name,
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)

        # All retries failed
        async with self._lock:
            self._on_failure()

        raise last_exception or Exception("Unknown error")

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.stats.last_failure_time is None:
            return True
        return time.time() - self.stats.last_failure_time >= self.config.timeout

    def _on_success(self) -> None:
        """Handle successful call."""
        self.stats.successes += 1
        self.stats.last_success_time = time.time()

        CIRCUIT_BREAKER_SUCCESSES.labels(service=self.service_name).inc()

        if self.state == CircuitState.HALF_OPEN:
            if self.stats.successes >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.stats.failures = 0
                logger.info("circuit_breaker_closed", service=self.service_name)

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.stats.failures += 1
        self.stats.last_failure_time = time.time()
        self.stats.recent_failures.append(time.time())

        CIRCUIT_BREAKER_FAILURES.labels(service=self.service_name).inc()

        if self.stats.failures >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                "circuit_breaker_opened", service=self.service_name, failures=self.stats.failures
            )

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state

    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        return {
            "state": self.state.name,
            "failures": self.stats.failures,
            "successes": self.stats.successes,
            "last_failure_time": self.stats.last_failure_time,
            "last_success_time": self.stats.last_success_time,
        }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""

    pass


# Global circuit breaker registry
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    service_name: str, config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """Get or create circuit breaker for a service."""
    if service_name not in _circuit_breakers:
        _circuit_breakers[service_name] = CircuitBreaker(service_name, config)
    return _circuit_breakers[service_name]


def with_circuit_breaker(service_name: str, config: Optional[CircuitBreakerConfig] = None):
    """Decorator to apply circuit breaker to a function."""
    circuit_breaker = get_circuit_breaker(service_name, config)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await circuit_breaker.call(func, *args, **kwargs)

        return wrapper

    return decorator
