from __future__ import annotations
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from src.config.logging import get_logger

logger = get_logger(__name__)

class LongHorizonProject(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    description: str
    objective: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    target_completion: Optional[datetime] = None
    status: str = "planning"
    milestone_ids: List[uuid.UUID] = Field(default_factory=list)

    async def initialize_project(self) -> bool:
        logger.info(f"Initializing long horizon project: {self.name}")
        self.status = "active"
        return True
