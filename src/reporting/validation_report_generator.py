from __future__ import annotations

import json
import csv
import io
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class ReportMetrics(BaseModel):
    model_config = {"from_attributes": True}
    
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    success_rate: float = 0.0
    average_score: float = 0.0
    total_skills_reused: int = 0
    strategies_improved: int = 0

class ValidationReport(BaseModel):
    model_config = {"from_attributes": True}
    
    report_id: UUID
    report_type: str  # "Daily", "Weekly", "Monthly"
    generated_at: datetime
    metrics: ReportMetrics
    insights: List[str] = Field(default_factory=list)
    
    def to_json(self) -> str:
        return self.model_dump_json(indent=2)
    
    def to_csv(self) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "report_id", "report_type", "generated_at", "total_runs", 
            "successful_runs", "failed_runs", "success_rate", 
            "average_score", "total_skills_reused", "strategies_improved"
        ])
        writer.writerow([
            str(self.report_id),
            self.report_type,
            self.generated_at.isoformat(),
            self.metrics.total_runs,
            self.metrics.successful_runs,
            self.metrics.failed_runs,
            self.metrics.success_rate,
            self.metrics.average_score,
            self.metrics.total_skills_reused,
            self.metrics.strategies_improved
        ])
        return output.getvalue()
        
    def to_markdown(self) -> str:
        return f"""# Validation Report ({self.report_type})
Generated At: {self.generated_at.isoformat()}
Report ID: {self.report_id}

## Metrics
- Total Runs: {self.metrics.total_runs}
- Successful Runs: {self.metrics.successful_runs}
- Failed Runs: {self.metrics.failed_runs}
- Success Rate: {self.metrics.success_rate:.2f}%
- Average Score: {self.metrics.average_score:.2f}
- Total Skills Reused: {self.metrics.total_skills_reused}
- Strategies Improved: {self.metrics.strategies_improved}

## Insights
{chr(10).join(f"- {insight}" for insight in self.insights)}
"""

    def to_pdf(self) -> bytes:
        # Mocked PDF generation
        pdf_content = f"PDF_MAGIC_HEADER\nValidation Report - {self.report_type}\n{self.to_markdown()}"
        return pdf_content.encode('utf-8')


class ValidationReportGenerator:
    def __init__(self):
        pass
        
    async def generate_report(
        self, 
        report_type: str, 
        start_date: datetime, 
        end_date: datetime,
        benchmark_runs: List[Any],
        validation_results: List[Any]
    ) -> ValidationReport:
        logger.info(f"Generating {report_type} report from {start_date} to {end_date}")
        
        # Aggregate metrics
        total_runs = len(benchmark_runs)
        successful_runs = sum(1 for r in benchmark_runs if getattr(r, 'status', '') == 'success')
        failed_runs = total_runs - successful_runs
        success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0.0
        
        scores = [getattr(r, 'score', 0.0) for r in benchmark_runs]
        average_score = sum(scores) / len(scores) if scores else 0.0
        
        skills_reused = sum(getattr(r, 'skills_reused', 0) for r in validation_results)
        strategies_improved = sum(getattr(r, 'strategies_improved', 0) for r in validation_results)
        
        metrics = ReportMetrics(
            total_runs=total_runs,
            successful_runs=successful_runs,
            failed_runs=failed_runs,
            success_rate=success_rate,
            average_score=average_score,
            total_skills_reused=skills_reused,
            strategies_improved=strategies_improved
        )
        
        report = ValidationReport(
            report_id=uuid4(),
            report_type=report_type,
            generated_at=datetime.utcnow(),
            metrics=metrics,
            insights=[
                f"{report_type} validation completed.",
                f"Observed success rate: {success_rate:.2f}%."
            ]
        )
        
        logger.info(f"Report {report.report_id} generated successfully")
        return report

    async def generate_daily_report(self, date: datetime, benchmark_runs: List[Any], validation_results: List[Any]) -> ValidationReport:
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        return await self.generate_report("Daily", start_date, end_date, benchmark_runs, validation_results)
        
    async def generate_weekly_report(self, date: datetime, benchmark_runs: List[Any], validation_results: List[Any]) -> ValidationReport:
        start_date = date - timedelta(days=date.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)
        return await self.generate_report("Weekly", start_date, end_date, benchmark_runs, validation_results)
        
    async def generate_monthly_report(self, date: datetime, benchmark_runs: List[Any], validation_results: List[Any]) -> ValidationReport:
        start_date = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if date.month == 12:
            end_date = date.replace(year=date.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            end_date = date.replace(month=date.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return await self.generate_report("Monthly", start_date, end_date, benchmark_runs, validation_results)
