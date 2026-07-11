from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class ValidationResultBase(BaseModel):
    target_type: str
    target_id: UUID
    is_valid: bool
    errors: Optional[List[Dict[str, Any]]] = None


class ValidationResultCreate(ValidationResultBase):
    pass


class ValidationResult(ValidationResultBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class GraphEvolutionSnapshotBase(BaseModel):
    graph_id: UUID
    node_count: int
    edge_count: int
    snapshot_data: Dict[str, Any]


class GraphEvolutionSnapshotCreate(GraphEvolutionSnapshotBase):
    pass


class GraphEvolutionSnapshot(GraphEvolutionSnapshotBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class SystemHealthSnapshotBase(BaseModel):
    cpu_usage: float
    memory_usage: float
    active_tasks: int
    health_score: float


class SystemHealthSnapshotCreate(SystemHealthSnapshotBase):
    pass


class SystemHealthSnapshot(SystemHealthSnapshotBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}
