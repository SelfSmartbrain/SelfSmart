from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel


class BenchmarkMetricBase(BaseModel):
    metric_name: str
    metric_value: float
    metadata: Optional[Dict[str, Any]] = None


class BenchmarkMetricCreate(BenchmarkMetricBase):
    run_id: UUID


class BenchmarkMetric(BenchmarkMetricBase):
    id: UUID
    run_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class BenchmarkRunBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "pending"


class BenchmarkRunCreate(BenchmarkRunBase):
    pass


class BenchmarkRunUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class BenchmarkRun(BenchmarkRunBase):
    id: UUID
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StrategyComparisonBase(BaseModel):
    baseline_strategy_id: UUID
    candidate_strategy_id: UUID
    comparison_results: Dict[str, Any]
    winner_id: Optional[UUID] = None


class StrategyComparisonCreate(StrategyComparisonBase):
    pass


class StrategyComparison(StrategyComparisonBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class SkillValidationBase(BaseModel):
    skill_id: UUID
    validation_score: float
    test_cases_passed: int
    test_cases_total: int


class SkillValidationCreate(SkillValidationBase):
    pass


class SkillValidation(SkillValidationBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}
