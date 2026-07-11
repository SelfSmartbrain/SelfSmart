from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

class StrategyCreate(BaseModel):
    name: str
    description: str
    model_config = {"from_attributes": True}

class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    success_rate: Optional[float] = None
    model_config = {"from_attributes": True}

class StrategyResponse(BaseModel):
    id: UUID
    name: str
    description: str
    success_rate: float
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}
