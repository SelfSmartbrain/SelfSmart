from __future__ import annotations
from datetime import datetime
from uuid import UUID, uuid4
from typing import List, Optional
from pydantic import BaseModel, Field
from src.config.logging import get_logger

logger = get_logger(__name__)

class CapabilityRegression(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    model_id: UUID
    capability_name: str
    previous_score: float
    current_score: float
    decline_percentage: float
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    severity: str

    model_config = {"from_attributes": True}

async def detect_regression(
    model_id: UUID,
    capability_name: str,
    previous_score: float,
    current_score: float,
    threshold: float = 0.05
) -> Optional[CapabilityRegression]:
    logger.info(f"Checking for regressions in {capability_name} for {model_id}")
    
    if previous_score <= 0:
        return None
        
    decline = (previous_score - current_score) / previous_score
    
    if decline > threshold:
        severity = "HIGH" if decline > 0.2 else ("MEDIUM" if decline > 0.1 else "LOW")
        return CapabilityRegression(
            model_id=model_id,
            capability_name=capability_name,
            previous_score=previous_score,
            current_score=current_score,
            decline_percentage=decline * 100.0,
            severity=severity
        )
    return None
