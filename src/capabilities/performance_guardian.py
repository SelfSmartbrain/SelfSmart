from __future__ import annotations
from typing import List
from uuid import UUID
from pydantic import BaseModel
from src.config.logging import get_logger
from src.capability.regression_detector import CapabilityRegression

logger = get_logger(__name__)

class GuardianReport(BaseModel):
    model_id: UUID
    total_regressions: int
    high_severity_count: int
    regressions: List[CapabilityRegression]
    action_required: bool

    model_config = {"from_attributes": True}

async def review_performance(
    model_id: UUID,
    regressions: List[CapabilityRegression]
) -> GuardianReport:
    logger.warning(f"Guardian reviewing performance for {model_id}, found {len(regressions)} regressions")
    
    high_severity = [r for r in regressions if r.severity == "HIGH"]
    
    return GuardianReport(
        model_id=model_id,
        total_regressions=len(regressions),
        high_severity_count=len(high_severity),
        regressions=regressions,
        action_required=len(high_severity) > 0 or len(regressions) > 3
    )
