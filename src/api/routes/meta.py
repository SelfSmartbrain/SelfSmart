"""API routes for meta-learning operations."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import (
    CurrentUser,
    DB_StrategyRepo,
    DB_SkillRepo,
    DB_LearningRepo,
    DB_AnalyticsRepo,
)
from src.api.schemas.meta import StrategyResponse, SkillResponse, PolicyResponse, MetricResponse
from src.db.enums import TaskType

router = APIRouter(prefix="/meta", tags=["meta-learning"])


@router.get("/strategies", response_model=list[StrategyResponse])
async def list_strategies(
    current_user: CurrentUser,
    strategy_repo: DB_StrategyRepo,
    task_type: TaskType | None = None,
    limit: int = Query(20, ge=1, le=100),
) -> Any:
    """List execution strategies."""
    # Ideally filtering by task_type, for now just list all
    strategies = await strategy_repo.list(limit=limit)
    if task_type:
        strategies = [s for s in strategies if s.task_type == task_type]
    return strategies


@router.get("/skills", response_model=list[SkillResponse])
async def list_skills(
    current_user: CurrentUser,
    skill_repo: DB_SkillRepo,
    limit: int = Query(20, ge=1, le=100),
) -> Any:
    """List reusable skills."""
    return await skill_repo.list(limit=limit)


@router.get("/policies", response_model=list[PolicyResponse])
async def list_policies(
    current_user: CurrentUser,
    learning_repo: DB_LearningRepo,
) -> Any:
    """List active learning policies."""
    return await learning_repo.get_active_policies()


@router.get("/metrics", response_model=MetricResponse)
async def get_metrics(
    current_user: CurrentUser,
    analytics_repo: DB_AnalyticsRepo,
) -> Any:
    """Get aggregated system performance metrics."""
    from src.db.enums import MetricType
    
    summary = {}
    for m_type in MetricType:
        avg = await analytics_repo.get_average_metric(user_id=current_user.id, metric_type=m_type)
        summary[m_type.value] = avg
        
    return MetricResponse(metrics=summary)
