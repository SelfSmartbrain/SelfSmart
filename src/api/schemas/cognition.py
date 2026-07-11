"""Pydantic schemas for the Cognition and Dashboard modules (Phase 7)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ResearchReflectionResponse(BaseModel):
    """Response schema for a research reflection entry."""

    model_config = {"from_attributes": True}

    id: UUID
    goal_id: UUID | None
    track_id: UUID | None
    success_score: float
    quality_score: float
    confidence_score: float
    completion_percentage: float
    lessons_learned: list[str]
    mistakes_found: list[str]
    improvement_suggestions: list[str]
    reflection_summary: str
    created_at: datetime


class FailurePatternResponse(BaseModel):
    """Response schema for a detected failure pattern."""

    model_config = {"from_attributes": True}

    id: UUID
    pattern_name: str
    description: str
    frequency: int
    severity: str
    recommended_fix: str
    last_seen: datetime


class ResearchStrategyResponse(BaseModel):
    """Response schema for a research strategy."""

    model_config = {"from_attributes": True}

    id: UUID
    name: str
    description: str
    goal_type: str
    domain: str
    success_rate: float
    average_quality: float
    times_used: int
    created_at: datetime


class SkillResponse(BaseModel):
    """Response schema for a discovered skill."""

    model_config = {"from_attributes": True}

    id: UUID
    name: str
    description: str
    skill_type: str
    usage_count: int
    success_rate: float
    average_duration: float | None
    created_at: datetime


class CognitiveMetricResponse(BaseModel):
    """Response schema for a single cognitive metric data-point."""

    model_config = {"from_attributes": True}

    id: UUID
    metric_name: str
    metric_value: float
    metadata_: dict | None
    recorded_at: datetime


class DashboardOverview(BaseModel):
    """Aggregate overview returned by the dashboard."""

    model_config = {"from_attributes": True}

    active_goals: int
    completed_goals: int
    active_tracks: int
    knowledge_concepts: int
    learning_velocity: float
    autonomy_score: float
    curiosity_score: float
    knowledge_growth: float


class StrategyRanking(BaseModel):
    """Ranked strategy entry used on the dashboard."""

    model_config = {"from_attributes": True}

    strategy_id: UUID
    name: str
    success_rate: float
    times_used: int
    average_quality: float


class TriggerReflectionRequest(BaseModel):
    """Request body to manually trigger a reflection cycle."""

    model_config = {"from_attributes": True}

    track_id: UUID


class GenerateStrategyRequest(BaseModel):
    """Request body to generate a new research strategy."""

    model_config = {"from_attributes": True}

    goal: str
    domain: str


class CognitionMetricsResponse(BaseModel):
    """Aggregated cognition metrics snapshot."""

    model_config = {"from_attributes": True}

    knowledge_growth_rate: float
    learning_velocity: float
    autonomy_score: float
    research_efficiency: float
    goal_completion_rate: float
    strategy_effectiveness: float
    skill_utilization: float
