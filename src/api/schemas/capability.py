from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

class CapabilityBase(BaseModel):
    name: str
    description: Optional[str] = None
    level: int = Field(default=1, ge=1, le=10)

class CapabilityCreate(CapabilityBase):
    pass

class CapabilityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    level: Optional[int] = Field(default=None, ge=1, le=10)

class CapabilityInDB(CapabilityBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

class ProgramBase(BaseModel):
    title: str
    objectives: List[str]
    is_active: bool = True

class ProgramCreate(ProgramBase):
    pass

class ProgramUpdate(BaseModel):
    title: Optional[str] = None
    objectives: Optional[List[str]] = None
    is_active: Optional[bool] = None

class ProgramInDB(ProgramBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

class ReviewBase(BaseModel):
    entity_id: UUID
    reviewer_id: UUID
    score: float = Field(ge=0.0, le=100.0)
    comments: Optional[str] = None

class ReviewCreate(ReviewBase):
    pass

class ReviewUpdate(BaseModel):
    score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    comments: Optional[str] = None

class ReviewInDB(ReviewBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}
