from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class RecoveryAction(BaseModel):
    model_config = {"from_attributes": True}
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    failure_id: uuid.UUID
    strategy_used: str
    status: str = "attempting"
    initiated_at: datetime = Field(default_factory=datetime.utcnow)

class RecoveryEngine:
    def __init__(self):
        self.actions: Dict[uuid.UUID, RecoveryAction] = {}

    async def initiate_recovery(self, failure_id: uuid.UUID, strategy: str = "retry") -> RecoveryAction:
        logger.info(f"Initiating recovery for failure {failure_id} using strategy: {strategy}")
        action = RecoveryAction(failure_id=failure_id, strategy_used=strategy)
        self.actions[action.id] = action
        return action

    async def finalize_recovery(self, action_id: uuid.UUID, success: bool) -> Optional[RecoveryAction]:
        logger.info(f"Finalizing recovery action {action_id}. Success: {success}")
        if action_id in self.actions:
            action = self.actions[action_id]
            action.status = "resolved" if success else "failed"
            return action
        return None
