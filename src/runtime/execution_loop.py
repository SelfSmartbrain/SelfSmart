"""Asynchronous execution loop for autonomous ModelX runtimes."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.autonomy.checkpoint_manager import CheckpointManager, RuntimeRecovery
from src.autonomy.objective_manager import Objective, ObjectiveManager
from src.autonomy.progress_tracker import ProgressTracker
from src.runtime.task_runtime import TaskRuntime


@dataclass
class LoopStepResult:
    tick: int
    status: str
    objective_id: str | None = None
    result: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "status": self.status,
            "objective_id": self.objective_id,
            "result": self.result or {},
        }


class ExecutionLoop:
    """Coordinates objective selection, cognition, task execution, and progress."""

    def __init__(
        self,
        objective_manager: ObjectiveManager | None = None,
        progress_tracker: ProgressTracker | None = None,
        task_runtime: TaskRuntime | None = None,
        cognitive_kernel: Any | None = None,
        checkpoint_manager: CheckpointManager | None = None,
        tick_interval: float = 1.0,
        auto_checkpoint_interval: int = 10,
    ) -> None:
        self.objective_manager = objective_manager or ObjectiveManager()
        self.progress_tracker = progress_tracker or ProgressTracker()
        self.task_runtime = task_runtime or TaskRuntime()
        self.cognitive_kernel = cognitive_kernel
        self.checkpoint_manager = checkpoint_manager
        self.runtime_recovery = RuntimeRecovery(checkpoint_manager) if checkpoint_manager else None
        self.tick_interval = tick_interval
        self.auto_checkpoint_interval = auto_checkpoint_interval
        self.tick_count = 0
        self.running = False

    async def step(self, session: Any = None) -> LoopStepResult:
        self.tick_count += 1
        objective = self.objective_manager.get_current_objective()
        if objective is None:
            return LoopStepResult(tick=self.tick_count, status="idle")

        await self.progress_tracker.track_progress(
            objective,
            "started",
            "Runtime tick started",
        )

        # Auto-checkpoint before critical operations
        if (
            self.runtime_recovery
            and session
            and self.tick_count % self.auto_checkpoint_interval == 0
        ):
            try:
                state_snapshot = {
                    "tick_count": self.tick_count,
                    "objective_id": objective.objective_id,
                    "objective_description": objective.description,
                    "running": self.running,
                }
                progress_snapshot = (
                    self.progress_tracker.to_dict()
                    if hasattr(self.progress_tracker, "to_dict")
                    else None
                )
                await self.runtime_recovery.auto_checkpoint_on_progress(
                    objective_id=(
                        objective.objective_id
                        if hasattr(objective, "objective_id")
                        else objective.objective_id
                    ),
                    session=session,
                    state_snapshot=state_snapshot,
                    progress_snapshot=progress_snapshot,
                )
            except Exception as checkpoint_exc:
                # Log checkpoint failure but don't fail the tick
                from src.config.logging import get_logger

                logger = get_logger(__name__)
                logger.warning(f"Failed to create auto-checkpoint: {checkpoint_exc}")

        try:
            cognitive_result = await self._process_objective(objective)
            task_result = await self.task_runtime.execute_task(
                {
                    "type": "execute_task",
                    "payload": {
                        "objective": objective.to_dict(),
                        "cognition": cognitive_result,
                        "processed_at": datetime.utcnow().isoformat(),
                    },
                }
            )
            status = "completed" if task_result["status"] == "completed" else task_result["status"]
            await self.progress_tracker.track_progress(
                objective,
                status,
                "Runtime tick completed",
                task_result,
            )
            return LoopStepResult(
                tick=self.tick_count,
                status=status,
                objective_id=objective.objective_id,
                result=task_result,
            )
        except Exception as exc:
            result = {"status": "failed", "error": str(exc)}
            await self.progress_tracker.track_progress(
                objective,
                "failed",
                str(exc),
                result,
            )

            # Create checkpoint on failure for recovery
            if self.runtime_recovery and session:
                try:
                    state_snapshot = {
                        "tick_count": self.tick_count,
                        "objective_id": objective.objective_id,
                        "error": str(exc),
                        "running": self.running,
                    }
                    await self.runtime_recovery.auto_checkpoint_before_critical(
                        objective_id=(
                            objective.objective_id
                            if hasattr(objective, "objective_id")
                            else objective.objective_id
                        ),
                        session=session,
                        state_snapshot=state_snapshot,
                        progress_snapshot=None,
                    )
                except Exception as checkpoint_exc:
                    from src.config.logging import get_logger

                    logger = get_logger(__name__)
                    logger.warning(f"Failed to create failure checkpoint: {checkpoint_exc}")

            return LoopStepResult(
                tick=self.tick_count,
                status="failed",
                objective_id=objective.objective_id,
                result=result,
            )

    async def run(self, max_steps: int | None = None) -> list[LoopStepResult]:
        self.running = True
        results: list[LoopStepResult] = []

        while self.running:
            result = await self.step()
            results.append(result)

            if max_steps is not None and len(results) >= max_steps:
                break

            await asyncio.sleep(self.tick_interval)

        self.running = False
        return results

    def stop(self) -> None:
        self.running = False

    async def _process_objective(self, objective: Objective) -> dict[str, Any]:
        if self.cognitive_kernel is None:
            return {
                "decision": {
                    "action": "plan",
                    "confidence": 0.5,
                    "reasoning": "No cognitive kernel configured",
                }
            }

        return await self.cognitive_kernel.process(
            {
                "type": "objective_tick",
                "query": objective.description,
                "objective": objective.to_dict(),
            },
            priority=objective.priority,
            require_attention=objective.priority >= 0.8,
        )
