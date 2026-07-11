"""
Goal-related API schemas.

Defines request/response models for goal creation, execution, and status tracking.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Priority(StrEnum):
    """Goal priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class GoalCreate(BaseModel):
    """Request schema for creating a new goal."""

    goal: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="High-level goal description",
        examples=["Research the latest advances in transformer architectures and summarize findings"],
    )
    context: str | None = Field(
        default=None,
        max_length=10000,
        description="Additional context or constraints for goal execution",
    )
    priority: Priority = Field(
        default=Priority.NORMAL,
        description="Goal priority level",
    )
    max_iterations: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of agent loop iterations",
    )


class GoalExecute(BaseModel):
    """Request schema for executing an existing goal."""

    resume: bool = Field(
        default=False,
        description="Whether to resume from a previous checkpoint",
    )
    override_max_iterations: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="Override the max iterations for this execution",
    )


class TaskSummaryInGoal(BaseModel):
    """Lightweight task summary embedded in goal responses."""

    id: uuid.UUID
    title: str
    status: str
    agent_type: str
    priority: int


class GoalResponse(BaseModel):
    """Response schema for goal details."""

    id: uuid.UUID
    goal: str
    status: str
    context: str | None = None
    tasks: list[TaskSummaryInGoal] = Field(default_factory=list)
    progress: float = Field(
        ge=0.0,
        le=1.0,
        description="Completion progress (0.0 to 1.0)",
    )
    total_tokens_used: int = 0
    created_at: datetime
    completed_at: datetime | None = None
    error: str | None = None

    model_config = {"from_attributes": True}


class GoalSummary(BaseModel):
    """Lightweight goal summary for list endpoints."""

    id: uuid.UUID
    goal: str
    status: str
    progress: float
    task_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class GoalListResponse(BaseModel):
    """Paginated list of goals."""

    goals: list[GoalSummary]
    total: int
    page: int
    page_size: int
