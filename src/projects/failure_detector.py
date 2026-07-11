from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class FailureAlert(BaseModel):
    model_config = {"from_attributes": True}
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    component_id: uuid.UUID
    error_message: str
    severity: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)

class FailureDetector:
    def __init__(self):
        self.alerts: List[FailureAlert] = []

    async def report_failure(self, component_id: uuid.UUID, error_message: str, severity: str = "high") -> FailureAlert:
        logger.error(f"Failure detected on {component_id}: {error_message}")
        alert = FailureAlert(
            component_id=component_id,
            error_message=error_message,
            severity=severity
        )
        self.alerts.append(alert)
        return alert

    async def get_recent_failures(self, limit: int = 10) -> List[FailureAlert]:
        logger.info(f"Retrieving up to {limit} recent failures")
        return sorted(self.alerts, key=lambda a: a.detected_at, reverse=True)[:limit]
