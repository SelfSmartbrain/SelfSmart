from __future__ import annotations
import asyncio
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import List
from pydantic import BaseModel, Field
from src.config.logging import get_logger

logger = get_logger(__name__)

class SystemHealthSnapshot(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    uptime_hours: float
    memory_usage_mb: float
    active_agents: int
    tasks_processed: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_config = {"from_attributes": True}

class LongHorizonRunner:
    def __init__(self) -> None:
        self.tasks_processed = 0

    async def run_horizon(self, duration_hours: int) -> List[SystemHealthSnapshot]:
        logger.info(f"Starting {duration_hours}-hour long horizon test (simulated).")
        snapshots = []

        # Simulate interval checks
        intervals = 4
        sleep_time_per_interval = 0.5  # Simulated sleep
        hours_per_interval = duration_hours / intervals

        for i in range(1, intervals + 1):
            await asyncio.sleep(sleep_time_per_interval)
            self.tasks_processed += int(100 * hours_per_interval)

            snapshot = SystemHealthSnapshot(
                uptime_hours=i * hours_per_interval,
                memory_usage_mb=256.0 + (i * 10),  # Simulated memory growth
                active_agents=10 + i,
                tasks_processed=self.tasks_processed
            )
            snapshots.append(snapshot)
            logger.info(f"Snapshot taken at {snapshot.uptime_hours}h: {snapshot.tasks_processed} tasks processed.")

        return snapshots
