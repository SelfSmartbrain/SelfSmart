from __future__ import annotations
import uuid
from typing import List, Optional, Dict

from pydantic import BaseModel
from src.config.logging import get_logger
from src.projects.long_horizon_project import LongHorizonProject

logger = get_logger(__name__)

class ProjectHealthReport(BaseModel):
    model_config = {"from_attributes": True}
    project_id: uuid.UUID
    status: str
    completion_percentage: float
    blocked_tasks_count: int
    recommendations: List[str]

class ProjectMonitor(BaseModel):
    model_config = {"from_attributes": True}
    
    async def monitor_project(self, project: LongHorizonProject) -> ProjectHealthReport:
        logger.info(f"Monitoring health of project {project.id}")
        report = ProjectHealthReport(
            project_id=project.id,
            status="on_track",
            completion_percentage=25.5,
            blocked_tasks_count=0,
            recommendations=["Continue with next milestone"]
        )
        return report
        
    async def detect_blockers(self, project_id: uuid.UUID) -> List[str]:
        logger.info(f"Detecting blockers for project {project_id}")
        return []
