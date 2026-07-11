"""Convenience runner for autonomous ModelX loops."""

from __future__ import annotations

import asyncio

from src.runtime.agent_runtime import AgentRuntime
from src.runtime.execution_loop import LoopStepResult


class AutonomousRunner:
    def __init__(self, runtime: AgentRuntime | None = None) -> None:
        self.runtime = runtime or AgentRuntime()

    async def run_autonomously_async(
        self,
        objective: str | None = None,
        max_steps: int = 1,
    ) -> list[LoopStepResult]:
        if objective:
            self.runtime.objective_manager.set_objective(objective)
        return await self.runtime.run(max_steps=max_steps)

    def run_autonomously(
        self,
        objective: str | None = None,
        max_steps: int = 1,
    ) -> list[dict]:
        results = asyncio.run(self.run_autonomously_async(objective, max_steps))
        return [result.to_dict() for result in results]
