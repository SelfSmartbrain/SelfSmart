from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class SandboxExecutionRequest(BaseModel):
    model_config = {"from_attributes": True}
    
    candidate_id: uuid.UUID
    run_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    env_overrides: Dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = 300

class SandboxExecutionResult(BaseModel):
    model_config = {"from_attributes": True}
    
    run_id: uuid.UUID
    candidate_id: uuid.UUID
    status: str
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: float
    started_at: datetime
    completed_at: datetime
