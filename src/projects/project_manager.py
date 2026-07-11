from __future__ import annotations
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from src.config.logging import get_logger
from src.projects.long_horizon_project import LongHorizonProject

logger = get_logger(__name__)

class ProjectManager(BaseModel):
    model_config = {"from_attributes": True}
    
    async def create_project(self, name: str, description: str, objective: str) -> LongHorizonProject:
        logger.info(f"Creating project: {name}")
        project = LongHorizonProject(
            name=name,
            description=description,
            objective=objective
        )
        return project
        
    async def get_active_projects(self) -> List[LongHorizonProject]:
        logger.info("Fetching active projects")
        return []
        
    async def update_project_status(self, project_id: uuid.UUID, status: str) -> bool:
        logger.info(f"Updating project {project_id} status to {status}")
        return True
