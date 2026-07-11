from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class ExecutionPlan(BaseModel):
    model_config = {"from_attributes": True}
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID
    steps: List[str]
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class ExecutionOrchestrator:
    def __init__(self):
        self.plans: Dict[uuid.UUID, ExecutionPlan] = {}

    async def create_plan(self, project_id: uuid.UUID, steps: List[str]) -> ExecutionPlan:
        logger.info(f"Creating execution plan for project {project_id}")
        plan = ExecutionPlan(project_id=project_id, steps=steps)
        self.plans[plan.id] = plan
        return plan

    async def start_execution(self, plan_id: uuid.UUID) -> bool:
        logger.info(f"Starting execution for plan {plan_id}")
        if plan_id in self.plans:
            plan = self.plans[plan_id]
            plan.status = "in_progress"
            plan.started_at = datetime.utcnow()
            return True
        return False

    async def stop_execution(self, plan_id: uuid.UUID) -> bool:
        logger.info(f"Stopping execution for plan {plan_id}")
        if plan_id in self.plans:
            plan = self.plans[plan_id]
            plan.status = "stopped"
            plan.completed_at = datetime.utcnow()
            return True
        return False
