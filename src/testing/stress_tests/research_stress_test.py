from __future__ import annotations
import asyncio
import time
from pydantic import BaseModel
from src.config.logging import get_logger

logger = get_logger(__name__)

class ResearchMetrics(BaseModel):
    concurrent_tracks: int
    completed_tracks: int
    failed_tracks: int
    duration_sec: float
    model_config = {"from_attributes": True}

class ResearchStressTester:
    async def mock_research_track(self, track_id: int) -> bool:
        try:
            # Simulate deep research taking some time
            await asyncio.sleep(0.1)
            return True
        except Exception as e:
            logger.error(f"Track {track_id} failed: {e}")
            return False

    async def run_stress_test(self, tracks: int = 500) -> ResearchMetrics:
        logger.info(f"Starting {tracks} simultaneous research tracks...")
        start_time = time.perf_counter()

        tasks = [self.mock_research_track(i) for i in range(tracks)]
        results = await asyncio.gather(*tasks)

        completed = sum(1 for r in results if r)
        failed = tracks - completed
        duration = time.perf_counter() - start_time

        return ResearchMetrics(
            concurrent_tracks=tracks,
            completed_tracks=completed,
            failed_tracks=failed,
            duration_sec=duration
        )
