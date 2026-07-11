from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

class ReflectionCreate(BaseModel):
    task_id: UUID
    content: str
    score: float
    model_config = {"from_attributes": True}

class ReflectionUpdate(BaseModel):
    content: Optional[str] = None
    score: Optional[float] = None
    model_config = {"from_attributes": True}

class ReflectionResponse(BaseModel):
    id: UUID
    task_id: UUID
    content: str
    score: float
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}
