from __future__ import annotations

import uuid
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class TaskResult(BaseModel):
    model_config = {"from_attributes": True}
    
    task_id: uuid.UUID
    status: str
    output: Any
    executed_at: datetime = Field(default_factory=datetime.utcnow)

class TaskExecutor:
    def __init__(self):
        pass

    async def execute_task(self, task_id: uuid.UUID, payload: Dict[str, Any]) -> TaskResult:
        logger.info(f"Executing task {task_id} with payload {payload}")
        
        await asyncio.sleep(0.1)
        
        return TaskResult(
            task_id=task_id,
            status="success",
            output={"result": "task completed successfully"}
        )

    async def cancel_task(self, task_id: uuid.UUID) -> bool:
        logger.info(f"Cancelling task {task_id}")
        return True
