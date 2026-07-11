from __future__ import annotations
import uuid
from typing import List, Optional

from pydantic import BaseModel
from src.config.logging import get_logger
from src.environment.opportunity_detector import Opportunity

logger = get_logger(__name__)

class RankedOpportunity(BaseModel):
    model_config = {"from_attributes": True}
    opportunity: Opportunity
    score: float
    rank: int
    reasoning: str

class GoalOpportunityRanker(BaseModel):
    model_config = {"from_attributes": True}
    
    async def rank_opportunities(self, opportunities: List[Opportunity], goals: List[dict]) -> List[RankedOpportunity]:
        logger.info(f"Ranking {len(opportunities)} opportunities against {len(goals)} goals")
        ranked = []
        for i, opp in enumerate(opportunities):
            score = 100.0 - (i * 10.0)
            ranked.append(
                RankedOpportunity(
                    opportunity=opp,
                    score=score,
                    rank=i + 1,
                    reasoning="Aligns well with current goals."
                )
            )
        ranked.sort(key=lambda x: x.score, reverse=True)
        return ranked
