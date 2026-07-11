from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class ImpactEvent(BaseModel):
    model_config = {"from_attributes": True}
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID
    event_type: str
    description: str
    recorded_at: datetime = Field(default_factory=datetime.utcnow)

class ImpactTracker:
    def __init__(self):
        self.events: List[ImpactEvent] = []

    async def record_impact(self, project_id: uuid.UUID, event_type: str, description: str) -> ImpactEvent:
        logger.info(f"Recording impact for project {project_id}: {event_type}")
        event = ImpactEvent(
            project_id=project_id,
            event_type=event_type,
            description=description
        )
        self.events.append(event)
        return event

    async def get_project_impacts(self, project_id: uuid.UUID) -> List[ImpactEvent]:
        logger.info(f"Retrieving impact events for project {project_id}")
        return [evt for evt in self.events if evt.project_id == project_id]
