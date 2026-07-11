"""
Reflection-related API schemas.

Defines response models for reflection reports and improvement insights.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SuccessRecord(BaseModel):
    """A successful outcome from a task execution."""

    task_id: uuid.UUID | None = None
    task_title: str
    description: str
    contributing_factors: list[str] = Field(default_factory=list)


class FailureRecord(BaseModel):
    """A failed outcome from a task execution."""

    task_id: uuid.UUID | None = None
    task_title: str
    error: str
    root_cause: str | None = None
    severity: str = "medium"


class ImprovementStrategy(BaseModel):
    """An actionable improvement strategy derived from reflection."""

    category: str = Field(description="Area of improvement (e.g., 'planning', 'research', 'execution')")
    description: str
    priority: str = "medium"
    applicable_scenarios: list[str] = Field(default_factory=list)
    expected_impact: str | None = None


class ReflectionResponse(BaseModel):
    """Detailed reflection report for a session."""

    id: uuid.UUID
    session_id: uuid.UUID
    task_id: uuid.UUID | None = None
    reflection_type: str
    successes: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    root_causes: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    confidence_score: float
    applied: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ReflectionInsight(BaseModel):
    """Aggregated insight from multiple reflection records."""

    pattern: str = Field(description="Identified pattern across reflections")
    frequency: int = Field(description="How often this pattern was observed")
    last_observed: datetime
    recommended_action: str
    confidence: float = Field(ge=0.0, le=1.0)


class ReflectionSummary(BaseModel):
    """Summary of reflection data for a session."""

    session_id: uuid.UUID
    total_reflections: int
    success_rate: float
    top_improvements: list[ImprovementStrategy]
    key_learnings: list[str]
    overall_confidence: float


class ReflectionListResponse(BaseModel):
    """List of reflection records."""

    reflections: list[ReflectionResponse]
    total: int
    insights: list[ReflectionInsight] = Field(default_factory=list)
