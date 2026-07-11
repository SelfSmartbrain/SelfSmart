from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel
from src.config.logging import get_logger

logger = get_logger(__name__)

class ExecutionProfile(BaseModel):
    model_config = {"from_attributes": True}
    
    entity_id: UUID
    entity_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    execution_time_ms: Optional[float] = None

class PerformanceProfiler:
    def __init__(self) -> None:
        self.profiles: Dict[UUID, List[ExecutionProfile]] = {}
        self.active_executions: Dict[UUID, ExecutionProfile] = {}

    async def start_profiling(self, entity_id: UUID, entity_type: str) -> None:
        profile = ExecutionProfile(
            entity_id=entity_id,
            entity_type=entity_type,
            start_time=datetime.utcnow()
        )
        self.active_executions[entity_id] = profile
        logger.info(f"Started profiling for {entity_type} {entity_id}")

    async def stop_profiling(self, entity_id: UUID) -> Optional[ExecutionProfile]:
        if entity_id not in self.active_executions:
            logger.warning(f"No active execution found for entity {entity_id}")
            return None
            
        profile = self.active_executions.pop(entity_id)
        profile.end_time = datetime.utcnow()
        profile.execution_time_ms = (profile.end_time - profile.start_time).total_seconds() * 1000
        
        if entity_id not in self.profiles:
            self.profiles[entity_id] = []
        self.profiles[entity_id].append(profile)
        
        logger.info(f"Stopped profiling for {profile.entity_type} {entity_id}. Time: {profile.execution_time_ms}ms")
        return profile

    async def get_average_execution_time(self, entity_id: UUID) -> float:
        if entity_id not in self.profiles or not self.profiles[entity_id]:
            return 0.0
            
        total_time = sum(p.execution_time_ms or 0 for p in self.profiles[entity_id])
        return total_time / len(self.profiles[entity_id])
