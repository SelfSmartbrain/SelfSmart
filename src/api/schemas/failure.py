from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel

class FailureCreate(BaseModel):
    task_id: UUID
    error_message: str
    context: Dict[str, Any]
    severity: str
    model_config = {"from_attributes": True}

class FailureUpdate(BaseModel):
    resolved: Optional[bool] = None
    resolution_notes: Optional[str] = None
    model_config = {"from_attributes": True}

class FailureResponse(BaseModel):
    id: UUID
    task_id: UUID
    error_message: str
    context: Dict[str, Any]
    severity: str
    resolved: bool
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}
