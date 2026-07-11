from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class Checkpoint(BaseModel):
    model_config = {"from_attributes": True}
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    workflow_id: uuid.UUID
    state_data: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CheckpointManager:
    def __init__(self):
        self.checkpoints: Dict[uuid.UUID, Checkpoint] = {}

    async def save_checkpoint(self, workflow_id: uuid.UUID, state_data: Dict[str, Any]) -> Checkpoint:
        logger.info(f"Saving checkpoint for workflow {workflow_id}")
        checkpoint = Checkpoint(workflow_id=workflow_id, state_data=state_data)
        self.checkpoints[checkpoint.id] = checkpoint
        return checkpoint

    async def load_checkpoint(self, checkpoint_id: uuid.UUID) -> Optional[Checkpoint]:
        logger.info(f"Loading checkpoint {checkpoint_id}")
        return self.checkpoints.get(checkpoint_id)
        
    async def get_latest_checkpoint(self, workflow_id: uuid.UUID) -> Optional[Checkpoint]:
        logger.info(f"Getting latest checkpoint for workflow {workflow_id}")
        workflow_checkpoints = [cp for cp in self.checkpoints.values() if cp.workflow_id == workflow_id]
        if not workflow_checkpoints:
            return None
        return max(workflow_checkpoints, key=lambda cp: cp.created_at)
