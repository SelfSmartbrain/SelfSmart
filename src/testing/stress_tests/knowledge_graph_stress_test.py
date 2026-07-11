from __future__ import annotations
import asyncio
import time
from pydantic import BaseModel
from src.config.logging import get_logger

logger = get_logger(__name__)

class GraphStressMetrics(BaseModel):
    total_inserts: int
    resolved_contradictions: int
    duration_sec: float
    inserts_per_sec: float
    model_config = {"from_attributes": True}

class GraphStressTester:
    async def mock_graph_insert(self, idx: int) -> bool:
        # Simulate Neo4j Insert
        await asyncio.sleep(0.02)
        return True

    async def mock_resolve_contradiction(self) -> bool:
        # Simulate contradiction resolution
        await asyncio.sleep(0.05)
        return True

    async def run_stress_test(self, inserts: int = 5000) -> GraphStressMetrics:
        logger.info(f"Starting massive concurrent graph inserts ({inserts})...")
        start_time = time.perf_counter()

        # Batch the inserts slightly to avoid memory issues
        batch_size = 500
        contradictions_resolved = 0

        for i in range(0, inserts, batch_size):
            batch = min(batch_size, inserts - i)
            tasks = [self.mock_graph_insert(j) for j in range(batch)]
            await asyncio.gather(*tasks)

            # Simulate a contradiction resolution every batch
            await self.mock_resolve_contradiction()
            contradictions_resolved += 1

        duration = time.perf_counter() - start_time

        return GraphStressMetrics(
            total_inserts=inserts,
            resolved_contradictions=contradictions_resolved,
            duration_sec=duration,
            inserts_per_sec=inserts / duration if duration > 0 else 0.0
        )
