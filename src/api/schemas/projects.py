from __future__ import annotations

from typing import List, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

class EnvironmentContextBase(BaseModel):
    model_config = {"from_attributes": True}
    
    context_data: dict

class EnvironmentContextCreate(EnvironmentContextBase):
    pass

class EnvironmentContextResponse(EnvironmentContextBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

class OpportunityBase(BaseModel):
    model_config = {"from_attributes": True}
    
    description: str
    potential_impact: float

class OpportunityCreate(OpportunityBase):
    pass

class OpportunityResponse(OpportunityBase):
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

class ProjectBase(BaseModel):
    model_config = {"from_attributes": True}
    
    name: str
    description: Optional[str] = None
    opportunity_id: Optional[UUID] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

class TaskBase(BaseModel):
    model_config = {"from_attributes": True}
    
    project_id: UUID
    title: str
    description: Optional[str] = None

class TaskCreate(TaskBase):
    pass

class TaskResponse(TaskBase):
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

class ImpactAnalysisBase(BaseModel):
    model_config = {"from_attributes": True}
    
    project_id: UUID
    impact_score: float
    details: dict

class ImpactAnalysisCreate(ImpactAnalysisBase):
    pass

class ImpactAnalysisResponse(ImpactAnalysisBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
