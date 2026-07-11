"""Pydantic schemas for meta-learning endpoints."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.db.enums import TaskType, StrategyStatus, MetricType, SkillStatus


class StrategyResponse(BaseModel):
    """Schema for returning a Strategy."""
    
    id: UUID
    task_type: TaskType
    name: str
    description: str
    success_rate: float
    confidence: float
    usage_count: int
    status: StrategyStatus
    is_global: bool
    tags: list[str] | None

    class Config:
        from_attributes = True


class SkillResponse(BaseModel):
    """Schema for returning a Skill."""
    
    id: UUID
    name: str
    description: str
    task_types: list[str]
    usage_count: int
    success_rate: float
    status: SkillStatus
    tags: list[str] | None

    class Config:
        from_attributes = True


class PolicyResponse(BaseModel):
    """Schema for returning a Policy."""
    
    id: UUID
    name: str
    description: str
    condition: str
    action: str
    confidence: float
    is_active: bool

    class Config:
        from_attributes = True


class MetricResponse(BaseModel):
    """Schema for returning aggregated metrics."""
    
    metrics: dict[str, float]
