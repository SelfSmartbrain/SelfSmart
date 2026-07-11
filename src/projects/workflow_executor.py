from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class WorkflowState(BaseModel):
    model_config = {"from_attributes": True}
    
    workflow_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    tasks: List[uuid.UUID]
    current_task_index: int = 0
    status: str = "initialized"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class WorkflowExecutor:
    def __init__(self):
        self.workflows: Dict[uuid.UUID, WorkflowState] = {}

    async def initialize_workflow(self, tasks: List[uuid.UUID]) -> WorkflowState:
        logger.info(f"Initializing workflow with {len(tasks)} tasks")
        state = WorkflowState(tasks=tasks)
        self.workflows[state.workflow_id] = state
        return state

    async def advance_workflow(self, workflow_id: uuid.UUID) -> Optional[WorkflowState]:
        logger.info(f"Advancing workflow {workflow_id}")
        if workflow_id in self.workflows:
            state = self.workflows[workflow_id]
            if state.current_task_index < len(state.tasks) - 1:
                state.current_task_index += 1
                state.status = "running"
            else:
                state.status = "completed"
            return state
        return None
