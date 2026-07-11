from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class ResourceAllocation(BaseModel):
    model_config = {"from_attributes": True}
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID
    resource_type: str
    amount: float
    allocated_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "active"

class ResourceManager:
    def __init__(self):
        self.allocations: Dict[uuid.UUID, ResourceAllocation] = {}

    async def allocate_resource(self, project_id: uuid.UUID, resource_type: str, amount: float) -> ResourceAllocation:
        logger.info(f"Allocating {amount} of {resource_type} for project {project_id}")
        allocation = ResourceAllocation(project_id=project_id, resource_type=resource_type, amount=amount)
        self.allocations[allocation.id] = allocation
        return allocation

    async def get_project_resources(self, project_id: uuid.UUID) -> List[ResourceAllocation]:
        logger.info(f"Retrieving resource allocations for project {project_id}")
        return [alloc for alloc in self.allocations.values() if alloc.project_id == project_id]

    async def release_resource(self, allocation_id: uuid.UUID) -> bool:
        logger.info(f"Releasing resource allocation {allocation_id}")
        if allocation_id in self.allocations:
            self.allocations[allocation_id].status = "released"
            return True
        return False
