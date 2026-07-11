"""
Task endpoints.

Provides task status retrieval and listing by goal.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from src.api.dependencies import CurrentUser, DB_TaskRepo
from src.api.schemas.tasks import TaskResponse, TaskListResponse, TaskSummary, ExecutionSummary
from src.config.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get task details",
)
async def get_task(
    task_id: uuid.UUID,
    user: CurrentUser,
    task_repo: DB_TaskRepo,
) -> TaskResponse:
    """Retrieve full details for a task including execution history."""
    task = await task_repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(
        id=task.id,
        session_id=task.session_id,
        parent_task_id=task.parent_task_id,
        title=task.title,
        description=task.description,
        status=task.status.value,
        priority=task.priority,
        agent_type=task.agent_type,
        dependencies=task.dependencies or [],
        result=task.result,
        error=task.error,
        retry_count=task.retry_count,
        subtasks=[],
        executions=[],
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
    )


@router.get(
    "/by-goal/{goal_id}",
    response_model=TaskListResponse,
    summary="List tasks for a goal",
)
async def list_tasks_by_goal(
    goal_id: uuid.UUID,
    user: CurrentUser,
    task_repo: DB_TaskRepo,
) -> TaskListResponse:
    """List all tasks belonging to a specific goal/session."""
    tasks = await task_repo.get_session_tasks(goal_id)

    summaries = [
        TaskSummary(
            id=t.id,
            title=t.title,
            status=t.status.value,
            agent_type=t.agent_type,
            priority=t.priority,
            created_at=t.created_at,
        )
        for t in tasks
    ]

    completed = sum(1 for t in tasks if t.status.value == "completed")
    failed = sum(1 for t in tasks if t.status.value == "failed")
    pending = sum(1 for t in tasks if t.status.value == "pending")

    return TaskListResponse(
        tasks=summaries,
        total=len(tasks),
        completed=completed,
        failed=failed,
        pending=pending,
    )
