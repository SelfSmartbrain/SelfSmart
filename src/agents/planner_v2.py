"""Long-Horizon Planner (v2)."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.config.settings import get_settings
from src.db.models import GeneratedGoal
from src.meta.goal_tree import GoalTreeEngine

logger = logging.getLogger(__name__)


class PlanStep(BaseModel):
    """A single step in a long-horizon plan."""
    id: str = Field(description="Unique string ID for the step, e.g. 'step_1'")
    title: str = Field(description="Title of the step")
    description: str = Field(description="Detailed instructions")
    deps: list[str] = Field(description="List of step IDs that must be completed before this one")


class LongHorizonPlan(BaseModel):
    """The complete long-horizon plan."""
    steps: list[PlanStep] = Field(description="List of all steps required to complete the goal")
    estimated_resources: str = Field(description="Estimation of resources (APIs, tools, tokens) needed")


class LongHorizonPlanner:
    """Capable of dynamic replanning and long-horizon dependency tracking."""

    def __init__(
        self,
        tree_engine: GoalTreeEngine,
        llm: Any = None,
    ) -> None:
        self.tree_engine = tree_engine
        self.settings = get_settings()

        if llm is None:
            from langchain_anthropic import ChatAnthropic
            # We use a large context model for 100+ step planning
            self.llm = ChatAnthropic(
                model=self.settings.anthropic_model,
                api_key=self.settings.anthropic_api_key.get_secret_value(),
                temperature=0.2,
                max_tokens=8192,
            )
        else:
            self.llm = llm

        self.structured_llm = self.llm.with_structured_output(LongHorizonPlan)

    async def create_plan(self, goal: GeneratedGoal) -> Any:
        """Generate a 100+ step capable plan and store it in the GoalTree."""
        logger.info(f"Generating long-horizon plan for goal {goal.id}")
        
        system_prompt = (
            "You are an elite autonomous research planner. Break down the provided research goal "
            "into a highly detailed, long-horizon plan. You must outline dependencies clearly. "
            "The plan may contain dozens of steps."
        )

        user_content = f"Goal Title: {goal.title}\nGoal Description: {goal.description}"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ]

        try:
            result: LongHorizonPlan = await self.structured_llm.ainvoke(messages)
            
            # Convert to dictionary format expected by GoalTreeEngine
            plan_steps = [
                {
                    "id": step.id,
                    "title": step.title,
                    "desc": step.description,
                    "deps": step.deps,
                }
                for step in result.steps
            ]
            
            tree = await self.tree_engine.generate_hierarchy(goal, plan_steps)
            logger.info(f"Long-horizon plan created successfully in Tree {tree.id}")
            return tree
            
        except Exception as e:
            logger.error(f"Long-horizon planning failed: {e}")
            return None
