from __future__ import annotations
import uuid
from typing import List, Optional, Dict

from pydantic import BaseModel
from src.config.logging import get_logger
from src.projects.task_decomposer import ProjectTask

logger = get_logger(__name__)

class DependencyPlanner(BaseModel):
    model_config = {"from_attributes": True}
    
    async def plan_dependencies(self, tasks: List[ProjectTask]) -> List[ProjectTask]:
        logger.info(f"Planning dependencies for {len(tasks)} tasks")
        # Example logic: task 2 depends on task 1
        if len(tasks) > 1:
            tasks[1].dependencies.append(tasks[0].id)
        return tasks
        
    async def get_execution_order(self, tasks: List[ProjectTask]) -> List[uuid.UUID]:
        logger.info("Determining execution order based on dependencies")
        # Simplistic topological sort placeholder
        return [task.id for task in tasks]
