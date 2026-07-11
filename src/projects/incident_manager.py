from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class Incident(BaseModel):
    model_config = {"from_attributes": True}
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    title: str
    description: str
    status: str = "open"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None

class IncidentManager:
    def __init__(self):
        self.incidents: Dict[uuid.UUID, Incident] = {}

    async def open_incident(self, title: str, description: str) -> Incident:
        logger.info(f"Opening incident: {title}")
        incident = Incident(title=title, description=description)
        self.incidents[incident.id] = incident
        return incident

    async def resolve_incident(self, incident_id: uuid.UUID) -> Optional[Incident]:
        logger.info(f"Resolving incident {incident_id}")
        if incident_id in self.incidents:
            incident = self.incidents[incident_id]
            incident.status = "resolved"
            incident.resolved_at = datetime.utcnow()
            return incident
        return None

    async def get_active_incidents(self) -> List[Incident]:
        return [inc for inc in self.incidents.values() if inc.status == "open"]
