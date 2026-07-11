from __future__ import annotations
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from src.config.logging import get_logger

logger = get_logger(__name__)

class Milestone(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID
    title: str
    description: str
    due_date: Optional[datetime] = None
    status: str = "pending"
    task_ids: List[uuid.UUID] = Field(default_factory=list)

class MilestoneGenerator(BaseModel):
    model_config = {"from_attributes": True}
    
    async def generate_milestones(self, project_id: uuid.UUID, objective: str) -> List[Milestone]:
        logger.info(f"Generating milestones for project {project_id} with objective: {objective}")
        milestones = [
            Milestone(project_id=project_id, title="Phase 1: Planning", description="Initial planning phase"),
            Milestone(project_id=project_id, title="Phase 2: Execution", description="Core implementation")
        ]
        return milestones
