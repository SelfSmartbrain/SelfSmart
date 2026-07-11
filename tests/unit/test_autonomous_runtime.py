from __future__ import annotations

import pytest

from src.autonomy.objective_manager import ObjectiveManager
from src.runtime.execution_loop import ExecutionLoop
from src.runtime.task_runtime import TaskRuntime
from src.safety.action_validator import ActionValidator


pytestmark = pytest.mark.asyncio


async def test_execution_loop_processes_active_objective() -> None:
    objective_manager = ObjectiveManager()
    objective = objective_manager.set_objective("Consolidate recent observations", priority=0.7)
    loop = ExecutionLoop(objective_manager=objective_manager, tick_interval=0)

    result = await loop.step()

    assert result.status == "completed"
    assert result.objective_id == objective.objective_id
    assert loop.progress_tracker.get_latest(objective.objective_id).status == "completed"


async def test_task_runtime_rejects_unsafe_actions() -> None:
    runtime = TaskRuntime(action_validator=ActionValidator())

    result = await runtime.execute_task(
        {"action": {"type": "shell_command", "command": "rm -rf /"}, "payload": "bad"}
    )

    assert result["status"] == "rejected"
    assert "requires explicit approval" in result["reason"]


async def test_task_runtime_executes_callable_tasks() -> None:
    runtime = TaskRuntime()

    result = await runtime.execute_task(
        {"type": "execute_task", "handler": lambda: {"ok": True}}
    )

    assert result["status"] == "completed"
    assert result["result"] == {"ok": True}
