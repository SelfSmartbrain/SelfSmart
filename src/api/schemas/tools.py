from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.db.enums import Priority


class CapabilityGapBase(BaseModel):
    description: str
    context: str | None = None
    priority: Priority = Priority.NORMAL
    impact: int = 1
    difficulty: int = 1
    estimated_value: float = 0.0
    status: str = "detected"


class CapabilityGapCreate(CapabilityGapBase):
    pass


class CapabilityGapResponse(CapabilityGapBase):
    id: UUID
    created_at: datetime
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}


class ToolBase(BaseModel):
    name: str
    description: str
    author: str = "system"
    is_active: bool = True


class ToolCreate(ToolBase):
    pass


class ToolResponse(ToolBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ToolVersionBase(BaseModel):
    tool_id: UUID
    version_string: str
    source_code: str
    dependencies: list[str] | None = None
    status: str = "testing"


class ToolVersionCreate(ToolVersionBase):
    pass


class ToolVersionResponse(ToolVersionBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ToolBenchmarkBase(BaseModel):
    tool_version_id: UUID
    latency_ms: float
    memory_mb: float
    cpu_percent: float
    success_rate: float
    error_rate: float
    output_quality: float


class ToolBenchmarkCreate(ToolBenchmarkBase):
    pass


class ToolBenchmarkResponse(ToolBenchmarkBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}
