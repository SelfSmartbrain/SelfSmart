from __future__ import annotations
from datetime import datetime
from uuid import UUID, uuid4
from typing import List
from pydantic import BaseModel, Field
from src.config.logging import get_logger
from src.capability.capability_growth_engine import GrowthMetrics
from src.capability.capability_comparator import CapabilityDelta

logger = get_logger(__name__)

class CapabilityReport(BaseModel):
    report_id: UUID = Field(default_factory=uuid4)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    growth_metrics: List[GrowthMetrics]
    comparisons: List[CapabilityDelta]
    summary: str

    model_config = {"from_attributes": True}

async def generate_capability_report(
    growth: List[GrowthMetrics], 
    comparisons: List[CapabilityDelta]
) -> CapabilityReport:
    logger.info("Generating capability report")
    
    summary = f"Report includes {len(growth)} growth metrics and {len(comparisons)} comparisons."
    
    return CapabilityReport(
        growth_metrics=growth,
        comparisons=comparisons,
        summary=summary
    )
