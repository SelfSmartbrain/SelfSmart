from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel

class CognitiveGenomeBase(BaseModel):
    architecture_id: UUID
    genome_data: Dict[str, Any]
    fitness_score: float
    generation: int
    is_active: bool = True

class CognitiveGenomeCreate(CognitiveGenomeBase):
    pass

class CognitiveGenomeUpdate(BaseModel):
    genome_data: Optional[Dict[str, Any]] = None
    fitness_score: Optional[float] = None
    is_active: Optional[bool] = None

class CognitiveGenomeResponse(CognitiveGenomeBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class ArchitecturePromotionBase(BaseModel):
    previous_architecture_id: Optional[UUID]
    new_architecture_id: UUID
    justification: str
    performance_metrics: Dict[str, Any]

class ArchitecturePromotionCreate(ArchitecturePromotionBase):
    pass

class ArchitecturePromotionUpdate(BaseModel):
    justification: Optional[str] = None
    performance_metrics: Optional[Dict[str, Any]] = None

class ArchitecturePromotionResponse(ArchitecturePromotionBase):
    id: UUID
    promoted_at: datetime

    model_config = {"from_attributes": True}
