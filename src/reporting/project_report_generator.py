from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from pydantic import BaseModel, Field
from src.config.logging import get_logger

logger = get_logger(__name__)

class ProjectMetric(BaseModel):
    model_config = {"from_attributes": True}
    
    metric_name: str
    value: float
    unit: str

class ProjectReport(BaseModel):
    model_config = {"from_attributes": True}
    
    report_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID
    report_type: str # 'daily', 'weekly'
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    summary: str
    metrics: List[ProjectMetric]
    status: str

class ProjectReportGenerator:
    """Generates daily and weekly reports for active projects."""
    
    async def generate_daily_report(self, project_id: uuid.UUID) -> ProjectReport:
        """Asynchronously generate a daily report for a specific project."""
        logger.info(f"Generating daily report for project: {project_id}")
        
        # Mocking report generation
        report = ProjectReport(
            project_id=project_id,
            report_type="daily",
            summary="Daily progress is on track. Minor latency in task execution observed.",
            metrics=[
                ProjectMetric(metric_name="tasks_completed", value=5.0, unit="count"),
                ProjectMetric(metric_name="resource_usage", value=75.5, unit="percentage"),
            ],
            status="Active"
        )
        logger.info(f"Daily report generated successfully: {report.report_id}")
        return report

    async def generate_weekly_report(self, project_id: uuid.UUID) -> ProjectReport:
        """Asynchronously generate a weekly report for a specific project."""
        logger.info(f"Generating weekly report for project: {project_id}")
        
        # Mocking report generation
        report = ProjectReport(
            project_id=project_id,
            report_type="weekly",
            summary="Weekly summary: Major milestones achieved in Phase 1. Ready for Phase 2 transition.",
            metrics=[
                ProjectMetric(metric_name="milestones_achieved", value=2.0, unit="count"),
                ProjectMetric(metric_name="average_velocity", value=42.0, unit="points/week"),
            ],
            status="Active"
        )
        logger.info(f"Weekly report generated successfully: {report.report_id}")
        return report
