"""High-level autonomous agent runtime facade."""

from __future__ import annotations

from typing import Any

from src.autonomy.objective_manager import ObjectiveManager
from src.autonomy.progress_tracker import ProgressTracker
from src.autonomy.checkpoint_manager import CheckpointManager
from src.runtime.execution_loop import ExecutionLoop, LoopStepResult
from src.runtime.task_runtime import TaskRuntime


class AgentRuntime:
    def __init__(
        self,
        cognitive_kernel: Any | None = None,
        objective_manager: ObjectiveManager | None = None,
        progress_tracker: ProgressTracker | None = None,
        task_runtime: TaskRuntime | None = None,
        checkpoint_manager: CheckpointManager | None = None,
        tick_interval: float = 1.0,
        auto_checkpoint_interval: int = 10,
    ) -> None:
        self.cognitive_kernel = cognitive_kernel
        self.objective_manager = objective_manager or ObjectiveManager()
        self.progress_tracker = progress_tracker or ProgressTracker()
        self.checkpoint_manager = checkpoint_manager
        self.execution_loop = ExecutionLoop(
            objective_manager=self.objective_manager,
            progress_tracker=self.progress_tracker,
            task_runtime=task_runtime or TaskRuntime(),
            cognitive_kernel=cognitive_kernel,
            checkpoint_manager=checkpoint_manager,
            tick_interval=tick_interval,
            auto_checkpoint_interval=auto_checkpoint_interval,
        )
        self.initialized = False

    async def initialize(self) -> None:
        if self.cognitive_kernel and hasattr(self.cognitive_kernel, "initialize"):
            await self.cognitive_kernel.initialize()
        self.initialized = True

    async def shutdown(self) -> None:
        self.execution_loop.stop()
        if self.cognitive_kernel and hasattr(self.cognitive_kernel, "shutdown"):
            await self.cognitive_kernel.shutdown()
        self.initialized = False

    async def run(self, max_steps: int | None = None) -> list[LoopStepResult]:
        if not self.initialized:
            await self.initialize()
        return await self.execution_loop.run(max_steps=max_steps)
