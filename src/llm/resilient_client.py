"""
Resilient LLM client with circuit breaker and retry logic.
"""

import asyncio
from typing import Optional

from src.resilience.circuit_breaker import (
    get_circuit_breaker,
    CircuitBreakerConfig,
    with_circuit_breaker,
)
from src.resilience.retry import with_retry, RetryConfig
from src.llm.provider import get_llm_client
from src.config.logging import get_logger

logger = get_logger(__name__)


class ResilientLLMClient:
    """LLM client with resilience patterns."""

    def __init__(self):
        # Circuit breaker for LLM calls
        self.circuit_breaker = get_circuit_breaker(
            "llm_api",
            CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=2,
                timeout=60.0,
                call_timeout=30.0,
                max_retries=3,
                retry_delay=1.0,
            ),
        )

        # Retry configuration
        self.retry_config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=True,
            retryable_exceptions=(
                ConnectionError,
                TimeoutError,
                asyncio.TimeoutError,
            ),
        )

    @with_retry(max_attempts=3, base_delay=1.0, max_delay=10.0, jitter=True)
    async def chat_completion(
        self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 2000, **kwargs
    ) -> dict:
        """Execute chat completion with resilience."""
        async with get_llm_client() as llm:
            return await llm.chat_completion(
                messages=messages, temperature=temperature, max_tokens=max_tokens, **kwargs
            )

    async def get_circuit_breaker_status(self) -> dict:
        """Get circuit breaker status."""
        return self.circuit_breaker.get_stats()


# Global resilient client instance
resilient_llm_client = ResilientLLMClient()
