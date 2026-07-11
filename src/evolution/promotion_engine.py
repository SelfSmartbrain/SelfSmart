from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from src.config.logging import get_logger

logger = get_logger(__name__)

class ArchitecturePromotion(BaseModel):
    promotion_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    candidate_id: uuid.UUID
    baseline_id: uuid.UUID
    promoted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    improvement_percentage: float
    details: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {"from_attributes": True}

class PromotionEngine:
    def __init__(self) -> None:
        pass
        
    async def evaluate_for_promotion(
        self,
        candidate_id: uuid.UUID,
        candidate_fitness: float,
        candidate_failure_rate: float,
        baseline_id: uuid.UUID,
        baseline_fitness: float,
        baseline_failure_rate: float
    ) -> Optional[ArchitecturePromotion]:
        logger.info(f"Evaluating candidate {candidate_id} against baseline {baseline_id}")
        
        if baseline_fitness == 0:
            baseline_fitness = 0.0001
            
        improvement = (candidate_fitness - baseline_fitness) / baseline_fitness
        
        if candidate_fitness > baseline_fitness * 1.05 and candidate_failure_rate < baseline_failure_rate:
            logger.info(f"Candidate {candidate_id} promoted! Improvement: {improvement:.2%}")
            return ArchitecturePromotion(
                candidate_id=candidate_id,
                baseline_id=baseline_id,
                improvement_percentage=improvement * 100,
                details={
                    "candidate_fitness": candidate_fitness,
                    "baseline_fitness": baseline_fitness,
                    "candidate_failure_rate": candidate_failure_rate,
                    "baseline_failure_rate": baseline_failure_rate
                }
            )
            
        logger.info(f"Candidate {candidate_id} not promoted.")
        return None
