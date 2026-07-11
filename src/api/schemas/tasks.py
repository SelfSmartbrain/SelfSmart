"""
Task-related API schemas.

Defines response models for task status and listing.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskSummary(BaseModel):
    """Lightweight task summary for list views."""

    id: uuid.UUID
    title: str
    status: str
    agent_type: str
    priority: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    """Detailed task response with execution history."""

    id: uuid.UUID
    session_id: uuid.UUID
    parent_task_id: uuid.UUID | None = None
    title: str
    description: str
    status: str
    priority: int
    agent_type: str
    dependencies: list[uuid.UUID] = Field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None
    retry_count: int = 0
    subtasks: list[TaskSummary] = Field(default_factory=list)
    executions: list[ExecutionSummary] = Field(default_factory=list)
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ExecutionSummary(BaseModel):
    """Execution record summary."""

    id: uuid.UUID
    agent_type: str
    status: str
    tokens_used: int
    duration_ms: int | None = None
    error: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    """List of tasks for a goal/session."""

    tasks: list[TaskSummary]
    total: int
    completed: int
    failed: int
    pending: int
