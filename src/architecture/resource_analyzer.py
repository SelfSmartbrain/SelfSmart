from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.config.logging import get_logger

logger = get_logger(__name__)

class ResourceSnapshot(BaseModel):
    model_config = {"from_attributes": True}
    
    entity_id: UUID
    timestamp: datetime
    queue_size: int
    memory_usage_mb: float

class ResourceAnalyzer:
    def __init__(self, scheduler: AsyncIOScheduler) -> None:
        self.scheduler = scheduler
        self.snapshots: Dict[UUID, List[ResourceSnapshot]] = {}
        self._tracking_jobs: Dict[UUID, str] = {}

    async def record_snapshot(self, snapshot: ResourceSnapshot) -> None:
        if snapshot.entity_id not in self.snapshots:
            self.snapshots[snapshot.entity_id] = []
        self.snapshots[snapshot.entity_id].append(snapshot)
        logger.debug(f"Recorded resource snapshot for {snapshot.entity_id}")

    async def start_continuous_tracking(self, entity_id: UUID, interval_seconds: int = 60) -> None:
        job_id = f"resource_track_{entity_id}"
        if job_id in self._tracking_jobs:
            logger.warning(f"Tracking already active for {entity_id}")
            return

        async def collect_metrics() -> None:
            snapshot = ResourceSnapshot(
                entity_id=entity_id,
                timestamp=datetime.utcnow(),
                queue_size=0,
                memory_usage_mb=0.0
            )
            await self.record_snapshot(snapshot)

        job = self.scheduler.add_job(collect_metrics, 'interval', seconds=interval_seconds, id=job_id)
        self._tracking_jobs[entity_id] = job.id
        logger.info(f"Started continuous resource tracking for {entity_id}")

    async def stop_continuous_tracking(self, entity_id: UUID) -> None:
        job_id = f"resource_track_{entity_id}"
        if job_id in self._tracking_jobs:
            self.scheduler.remove_job(job_id)
            del self._tracking_jobs[entity_id]
            logger.info(f"Stopped resource tracking for {entity_id}")
            
    async def get_latest_snapshot(self, entity_id: UUID) -> Optional[ResourceSnapshot]:
        if entity_id in self.snapshots and self.snapshots[entity_id]:
            return self.snapshots[entity_id][-1]
        return None
