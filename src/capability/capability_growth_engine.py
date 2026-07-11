from __future__ import annotations
from datetime import datetime
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel
from src.config.logging import get_logger

logger = get_logger(__name__)

class GrowthMetrics(BaseModel):
    capability_name: str
    previous_score: float
    current_score: float
    growth_rate: float
    generation_delta: int

    model_config = {"from_attributes": True}

async def calculate_growth(
    capability_name: str, 
    previous_score: float, 
    current_score: float, 
    gen_delta: int
) -> GrowthMetrics:
    logger.info(f"Calculating growth for {capability_name}")
    growth_rate = 0.0
    if previous_score > 0 and gen_delta > 0:
        growth_rate = ((current_score - previous_score) / previous_score) / gen_delta
        
    return GrowthMetrics(
        capability_name=capability_name,
        previous_score=previous_score,
        current_score=current_score,
        growth_rate=growth_rate,
        generation_delta=gen_delta
    )
