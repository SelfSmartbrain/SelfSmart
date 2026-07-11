"""Task execution helpers for the autonomous runtime."""

from __future__ import annotations

import inspect
from typing import Any, Awaitable, Callable

from src.safety.action_validator import ActionValidator, ValidationResult


class TaskRuntime:
    """Executes safe in-process tasks and returns structured outcomes."""

    def __init__(self, action_validator: ActionValidator | None = None) -> None:
        self.action_validator = action_validator or ActionValidator()

    async def execute_task(self, task: Any) -> dict[str, Any]:
        validation = self.action_validator.validate_action(self._action_for(task))
        if not validation:
            return {
                "status": "rejected",
                "reason": validation.reason,
                "warnings": validation.warnings,
            }

        try:
            result = await self._run_task(task)
            return {
                "status": "completed",
                "result": result,
                "warnings": validation.warnings,
            }
        except Exception as exc:
            return {"status": "failed", "error": str(exc), "warnings": validation.warnings}

    def _action_for(self, task: Any) -> Any:
        if isinstance(task, dict):
            return task.get("action") or {"type": task.get("type", "execute_task"), "task": task}
        return {"type": "execute_task", "task": str(task)}

    async def _run_task(self, task: Any) -> Any:
        if isinstance(task, dict):
            handler = task.get("handler") or task.get("callable")
            if handler is not None:
                return await self._call(handler, *task.get("args", ()), **task.get("kwargs", {}))
            return task.get("payload", task)

        if callable(task):
            return await self._call(task)

        return task

    async def _call(self, handler: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        value = handler(*args, **kwargs)
        if inspect.isawaitable(value):
            return await value
        return value
