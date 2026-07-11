from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

class SkillCreate(BaseModel):
    name: str
    description: str
    model_config = {"from_attributes": True}

class SkillUpdate(BaseModel):
    proficiency: Optional[float] = None
    model_config = {"from_attributes": True}

class SkillResponse(BaseModel):
    id: UUID
    name: str
    description: str
    proficiency: float
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}
