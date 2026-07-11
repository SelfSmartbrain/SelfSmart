from __future__ import annotations

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class InnovationMetrics(BaseModel):
    model_config = {"from_attributes": True}
    
    overall_innovation_score: float = 0.0
    total_discoveries: int = 0
    top_discoveries: List[UUID] = Field(default_factory=list)

class InnovationIndex(BaseModel):
    model_config = {"from_attributes": True}
    
    metrics_history: List[InnovationMetrics] = Field(default_factory=list)

    async def calculate_index(self, discoveries: List[Any]) -> InnovationMetrics:
        logger.info("Calculating innovation index.")
        
        if not discoveries:
            return InnovationMetrics()
            
        total_score = sum(d.discovery_score for d in discoveries)
        sorted_discoveries = sorted(discoveries, key=lambda x: x.discovery_score, reverse=True)
        
        metrics = InnovationMetrics(
            overall_innovation_score=total_score / len(discoveries),
            total_discoveries=len(discoveries),
            top_discoveries=[d.discovery_id for d in sorted_discoveries[:5]]
        )
        self.metrics_history.append(metrics)
        return metrics
