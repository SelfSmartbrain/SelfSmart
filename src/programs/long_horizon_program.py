from __future__ import annotations

from typing import List, Optional, Dict
from uuid import UUID, uuid4
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class ProgramMilestone(BaseModel):
    model_config = {"from_attributes": True}
    
    milestone_id: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    is_completed: bool = False
    completed_at: Optional[datetime] = None

class LongHorizonProgram(BaseModel):
    model_config = {"from_attributes": True}
    
    program_id: UUID = Field(default_factory=uuid4)
    name: str
    objective: str
    duration_months: int
    milestones: List[ProgramMilestone] = Field(default_factory=list)
    start_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "Active"

    async def add_milestone(self, title: str, description: str) -> ProgramMilestone:
        logger.info(f"Adding milestone to program {self.program_id}")
        milestone = ProgramMilestone(title=title, description=description)
        self.milestones.append(milestone)
        return milestone

    async def complete_milestone(self, milestone_id: UUID) -> Optional[ProgramMilestone]:
        logger.info(f"Marking milestone {milestone_id} as complete")
        for ms in self.milestones:
            if ms.milestone_id == milestone_id:
                ms.is_completed = True
                ms.completed_at = datetime.now(timezone.utc)
                return ms
        return None
