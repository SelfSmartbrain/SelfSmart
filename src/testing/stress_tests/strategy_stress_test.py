from __future__ import annotations
import asyncio
import time
from pydantic import BaseModel
from src.config.logging import get_logger

logger = get_logger(__name__)

class StrategyMetrics(BaseModel):
    concurrent_requests: int
    successful_strategies: int
    throughput: float
    model_config = {"from_attributes": True}

class StrategyStressTester:
    async def mock_generate_strategy(self) -> bool:
        # Simulate heavy compute/LLM call
        await asyncio.sleep(0.05)
        return True

    async def run_stress_test(self, concurrent_requests: int = 200) -> StrategyMetrics:
        logger.info(f"Hammering strategy optimizer with {concurrent_requests} requests...")
        start_time = time.perf_counter()

        tasks = [self.mock_generate_strategy() for _ in range(concurrent_requests)]
        results = await asyncio.gather(*tasks)

        successful = sum(1 for r in results if r)
        duration = time.perf_counter() - start_time

        return StrategyMetrics(
            concurrent_requests=concurrent_requests,
            successful_strategies=successful,
            throughput=concurrent_requests / duration if duration > 0 else 0.0
        )
