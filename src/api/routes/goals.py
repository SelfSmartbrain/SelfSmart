"""
Goal management endpoints.

Provides CRUD operations for goals and triggers goal execution
through the runtime execution loop.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from src.api.dependencies import CurrentUser, DB_SessionRepo, DB_TaskRepo
from src.api.schemas.goals import (
    GoalCreate,
    GoalExecute,
    GoalListResponse,
    GoalResponse,
    GoalSummary,
)
from src.config.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=GoalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new goal",
)
async def create_goal(
    body: GoalCreate,
    user: CurrentUser,
    session_repo: DB_SessionRepo,
) -> GoalResponse:
    """
    Create a new goal and prepare it for execution.

    This creates a session record in the database but does NOT start
    execution. Use POST /goals/{id}/execute to begin.
    """
    session = await session_repo.create_session(
        user_id=user.id,
        goal=body.goal,
        context={"priority": body.priority, "max_iterations": body.max_iterations},
    )

    logger.info("Goal created", session_id=str(session.id), goal=body.goal[:80])

    return GoalResponse(
        id=session.id,
        goal=session.goal,
        status=session.status.value,
        context=body.context,
        tasks=[],
        progress=0.0,
        total_tokens_used=0,
        created_at=session.created_at,
        completed_at=None,
        error=None,
    )


@router.get(
    "/{goal_id}",
    response_model=GoalResponse,
    summary="Get goal details",
)
async def get_goal(
    goal_id: uuid.UUID,
    user: CurrentUser,
    session_repo: DB_SessionRepo,
    task_repo: DB_TaskRepo,
) -> GoalResponse:
    """Retrieve full details for a goal including its tasks."""
    session = await session_repo.get_session(goal_id)
    if not session:
        raise HTTPException(status_code=404, detail="Goal not found")

    tasks = await task_repo.get_session_tasks(goal_id)
    completed = sum(1 for t in tasks if t.status.value == "completed")
    total = len(tasks) or 1

    from src.api.schemas.goals import TaskSummaryInGoal

    task_summaries = [
        TaskSummaryInGoal(
            id=t.id,
            title=t.title,
            status=t.status.value,
            agent_type=t.agent_type,
            priority=t.priority,
        )
        for t in tasks
    ]

    return GoalResponse(
        id=session.id,
        goal=session.goal,
        status=session.status.value,
        tasks=task_summaries,
        progress=completed / total,
        total_tokens_used=0,
        created_at=session.created_at,
        completed_at=session.completed_at,
    )


@router.get(
    "",
    response_model=GoalListResponse,
    summary="List goals",
)
async def list_goals(
    user: CurrentUser,
    session_repo: DB_SessionRepo,
    page: int = 1,
    page_size: int = 20,
) -> GoalListResponse:
    """List all goals for the current user with pagination."""
    offset = (page - 1) * page_size
    sessions = await session_repo.get_user_sessions(user.id, offset=offset, limit=page_size)

    summaries = [
        GoalSummary(
            id=s.id,
            goal=s.goal,
            status=s.status.value,
            progress=0.0,
            task_count=0,
            created_at=s.created_at,
        )
        for s in sessions
    ]

    return GoalListResponse(
        goals=summaries,
        total=len(summaries),
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{goal_id}/execute",
    response_model=dict[str, Any],
    summary="Execute a goal",
)
async def execute_goal(
    goal_id: uuid.UUID,
    body: GoalExecute,
    user: CurrentUser,
    session_repo: DB_SessionRepo,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """
    Start executing a goal through the orchestrator agent pipeline.

    The execution runs as a background task. Poll GET /goals/{id}
    to track progress.
    """
    session = await session_repo.get_session(goal_id)
    if not session:
        raise HTTPException(status_code=404, detail="Goal not found")

    from src.db.enums import SessionStatus

    await session_repo.update_status(goal_id, SessionStatus.ACTIVE)

    async def _run_goal() -> None:
        """Background task: push the goal into the runtime ObjectiveManager."""
        try:
            from src.runtime.runtime_singleton import get_runtime

            runtime = get_runtime()
            priority = float(
                (body.context or {}).get("priority", 0.5) if hasattr(body, "context") else 0.5
            )
            obj = runtime.objective_manager.set_objective(
                session.goal,
                priority=priority,
                metadata={"session_id": str(goal_id), "user_id": str(user.id)},
            )
            logger.info("Objective pushed to runtime", objective_id=obj.objective_id)
        except RuntimeError as exc:
            # Runtime not yet initialized (very early startup race)
            logger.error(
                "Runtime not available for goal execution",
                goal_id=str(goal_id),
                error=str(exc),
            )
            from src.db.enums import SessionStatus

            await session_repo.update_status(goal_id, SessionStatus.FAILED)
        except Exception as exc:
            logger.error("Goal execution failed", goal_id=str(goal_id), error=str(exc))
            from src.db.enums import SessionStatus

            await session_repo.update_status(goal_id, SessionStatus.FAILED)

    background_tasks.add_task(_run_goal)

    return {
        "message": "Goal execution started",
        "goal_id": str(goal_id),
        "status": "active",
    }
