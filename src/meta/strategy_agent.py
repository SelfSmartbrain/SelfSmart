"""Strategy Agent component."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.config.settings import get_settings
from src.db.enums import TaskType
from src.db.repositories.skill_repo import SkillRepository
from src.meta.strategy_engine import StrategyEngine

logger = logging.getLogger(__name__)


class SynthesizedStrategy(BaseModel):
    """Output format for a dynamically synthesized strategy."""
    
    name: str = Field(description="A concise name for the custom strategy.")
    description: str = Field(description="A detailed description of the approach.")
    steps: list[dict[str, Any]] = Field(description="The sequential steps to execute.")
    skills_used: list[str] = Field(description="Names of reusable skills leveraged in this strategy.")
    confidence: float = Field(description="Estimated likelihood of success (0.0 to 1.0).")
    justification: str = Field(description="Why this approach is expected to work.")


class StrategyAgent:
    """Specialized agent that devises novel strategies for complex tasks."""

    def __init__(
        self,
        strategy_engine: StrategyEngine,
        skill_repo: SkillRepository,
        llm: Any = None,
    ) -> None:
        self.strategy_engine = strategy_engine
        self.skill_repo = skill_repo
        self.settings = get_settings()

        if llm is None:
            from langchain_anthropic import ChatAnthropic
            self.llm = ChatAnthropic(
                model=self.settings.anthropic_model,
                api_key=self.settings.anthropic_api_key.get_secret_value(),
                temperature=0.4,
            )
        else:
            self.llm = llm

        self.structured_llm = self.llm.with_structured_output(SynthesizedStrategy)

    async def synthesize(
        self,
        goal: str,
        task_type: TaskType | str,
        context: str | None = None,
        constraints: list[str] | None = None,
    ) -> dict[str, Any]:
        """Synthesize a custom strategy when existing ones are insufficient."""
        logger.info("Synthesizing custom strategy", goal=goal[:50])

        # Fetch available active skills to use as building blocks
        active_skills = await self.skill_repo.search(task_type=task_type, limit=10)
        skills_summary = [
            f"- {skill.name}: {skill.description} (Success rate: {skill.success_rate:.2f})"
            for skill in active_skills
        ]

        # Fetch top baseline strategies for inspiration
        baseline_strategies = await self.strategy_engine.get_strategies(task_type=task_type, limit=3)
        baselines_summary = [
            f"- {strat.name}: {strat.description} (Success rate: {strat.success_rate:.2f})"
            for strat in baseline_strategies
        ]

        system_prompt = (
            "You are an expert Strategy Agent for an AGI-inspired platform. Your goal is to "
            "design a highly effective, robust execution strategy for a complex task.\n\n"
            "You should leverage existing skills and draw inspiration from past successful strategies, "
            "while adapting to the unique requirements and constraints of the current goal."
        )

        user_content = (
            f"Goal: {goal}\n"
            f"Task Type: {task_type}\n"
        )
        if context:
            user_content += f"Context: {context}\n"
        if constraints:
            user_content += f"Constraints:\n" + "\n".join([f"- {c}" for c in constraints]) + "\n"

        if skills_summary:
            user_content += "\nAvailable Reusable Skills:\n" + "\n".join(skills_summary) + "\n"
        if baselines_summary:
            user_content += "\nTop Baseline Strategies:\n" + "\n".join(baselines_summary) + "\n"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ]

        try:
            result: SynthesizedStrategy = await self.structured_llm.ainvoke(messages)
            
            # Optionally, we could immediately save this to the strategy engine in "testing" status
            strategy_record = await self.strategy_engine.create_strategy(
                task_type=task_type,
                name=result.name,
                description=result.description,
                steps=result.steps,
                confidence=result.confidence,
                tags=result.skills_used,
            )
            
            return {
                "id": str(strategy_record.id),
                "name": result.name,
                "description": result.description,
                "steps": result.steps,
                "confidence": result.confidence,
                "justification": result.justification,
            }

        except Exception as e:
            logger.error(f"Strategy synthesis failed: {e}")
            return {
                "error": str(e),
                "status": "failed",
            }
