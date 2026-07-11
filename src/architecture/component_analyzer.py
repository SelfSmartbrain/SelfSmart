from __future__ import annotations

import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from uuid import UUID

from pydantic import BaseModel
from src.config.logging import get_logger

logger = get_logger(__name__)

class ComponentLog(BaseModel):
    model_config = {"from_attributes": True}
    
    component_id: UUID
    timestamp: datetime
    latency_ms: float
    memory_mb: float

class ComponentHealthScore(BaseModel):
    model_config = {"from_attributes": True}
    
    component_id: UUID
    health_score: float
    rank: int

class ComponentAnalyzer:
    def __init__(self) -> None:
        self.logs: Dict[UUID, List[ComponentLog]] = {}

    async def add_log(self, log: ComponentLog) -> None:
        if log.component_id not in self.logs:
            self.logs[log.component_id] = []
        self.logs[log.component_id].append(log)
        logger.info(f"Added log for component {log.component_id}")

    async def analyze_health(self) -> List[ComponentHealthScore]:
        logger.info("Analyzing component health based on latency and memory")
        scores = []
        for component_id, component_logs in self.logs.items():
            if not component_logs:
                continue
            
            avg_latency = sum(log.latency_ms for log in component_logs) / len(component_logs)
            avg_memory = sum(log.memory_mb for log in component_logs) / len(component_logs)
            
            # Simple scoring mechanism (lower latency and memory gives a higher score)
            score = 100.0 - (avg_latency * 0.1) - (avg_memory * 0.05)
            score = max(0.0, min(100.0, score))
            scores.append((component_id, score))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        health_scores = []
        for rank, (comp_id, score) in enumerate(scores, start=1):
            health_scores.append(ComponentHealthScore(
                component_id=comp_id,
                health_score=score,
                rank=rank
            ))
            
        return health_scores
