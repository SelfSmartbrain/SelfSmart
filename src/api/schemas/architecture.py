from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

class ArchitectureVersionBase(BaseModel):
    version_name: str
    description: Optional[str] = None
    fitness_score: float = 0.0

class ArchitectureVersionCreate(ArchitectureVersionBase):
    pass

class ArchitectureVersionResponse(ArchitectureVersionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ArchitectureComponentBase(BaseModel):
    version_id: UUID
    name: str
    component_type: str
    health_score: float = 0.0

class ArchitectureComponentCreate(ArchitectureComponentBase):
    pass

class ArchitectureComponentResponse(ArchitectureComponentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class BottleneckBase(BaseModel):
    component_id: UUID
    severity: str
    description: str

class BottleneckCreate(BottleneckBase):
    pass

class BottleneckResponse(BottleneckBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CandidateBase(BaseModel):
    version_id: UUID
    proposed_changes: str
    estimated_improvement: float = 0.0

class CandidateCreate(CandidateBase):
    pass

class CandidateResponse(CandidateBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class BenchmarkBase(BaseModel):
    candidate_id: UUID
    metric_name: str
    value: float

class BenchmarkCreate(BenchmarkBase):
    pass

class BenchmarkResponse(BenchmarkBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
