from __future__ import annotations
import asyncio
import time
from typing import List
from pydantic import BaseModel
from src.config.logging import get_logger

logger = get_logger(__name__)

class GoalStressMetrics(BaseModel):
    goal_count: int
    success_count: int
    failure_count: int
    total_time_sec: float
    throughput_per_sec: float
    avg_latency_ms: float
    model_config = {"from_attributes": True}

class GoalStressTest:
    async def mock_process_goal(self) -> float:
        start = time.perf_counter()
        await asyncio.sleep(0.01) # Simulated network/db IO
        return (time.perf_counter() - start) * 1000

    async def run_batch(self, count: int) -> GoalStressMetrics:
        logger.info(f"Starting goal stress test with {count} goals...")
        start_time = time.perf_counter()

        tasks = [self.mock_process_goal() for _ in range(count)]
        latencies = await asyncio.gather(*tasks, return_exceptions=True)

        successes = [l for l in latencies if isinstance(l, float)]
        failures = len(latencies) - len(successes)

        total_time = time.perf_counter() - start_time
        avg_latency = sum(successes) / len(successes) if successes else 0.0
        throughput = count / total_time if total_time > 0 else 0.0

        return GoalStressMetrics(
            goal_count=count,
            success_count=len(successes),
            failure_count=failures,
            total_time_sec=total_time,
            throughput_per_sec=throughput,
            avg_latency_ms=avg_latency
        )

    async def run_all_tiers(self) -> List[GoalStressMetrics]:
        tiers = [100, 500, 1000, 5000]
        results = []
        for t in tiers:
            result = await self.run_batch(t)
            results.append(result)
        return results
