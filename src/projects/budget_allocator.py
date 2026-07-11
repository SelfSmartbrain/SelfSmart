from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class Budget(BaseModel):
    model_config = {"from_attributes": True}
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID
    total_tokens: int
    used_tokens: int = 0
    api_limit_per_minute: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

class BudgetAllocator:
    def __init__(self):
        self.budgets: Dict[uuid.UUID, Budget] = {}

    async def set_project_budget(self, project_id: uuid.UUID, total_tokens: int, api_limit: int) -> Budget:
        logger.info(f"Setting budget for project {project_id}: {total_tokens} tokens")
        budget = Budget(project_id=project_id, total_tokens=total_tokens, api_limit_per_minute=api_limit)
        self.budgets[project_id] = budget
        return budget

    async def consume_budget(self, project_id: uuid.UUID, tokens: int) -> bool:
        logger.info(f"Consuming {tokens} tokens for project {project_id}")
        if project_id in self.budgets:
            budget = self.budgets[project_id]
            if budget.used_tokens + tokens <= budget.total_tokens:
                budget.used_tokens += tokens
                return True
            else:
                logger.warning(f"Budget exceeded for project {project_id}")
                return False
        return False

    async def get_budget_status(self, project_id: uuid.UUID) -> Optional[Budget]:
        return self.budgets.get(project_id)
