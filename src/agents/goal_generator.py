"""Autonomous Goal Generator."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.config.settings import get_settings
from src.db.models import GeneratedGoal, KnowledgeGap
from src.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ProposedGoal(BaseModel):
    """Structured output for an LLM-generated goal."""
    title: str = Field(description="A concise, actionable title for the goal.")
    description: str = Field(description="Detailed explanation of what the goal aims to achieve.")
    relevance_score: float = Field(description="How relevant this goal is to the input gap (0.0 to 1.0).")


class GoalGenerator:
    """Generates useful goals from knowledge gaps, failures, and curiosity scores."""

    def __init__(
        self,
        goal_repo: BaseRepository[GeneratedGoal],
        llm: Any = None,
    ) -> None:
        self.goal_repo = goal_repo
        self.settings = get_settings()

        if llm is None:
            from langchain_anthropic import ChatAnthropic
            self.llm = ChatAnthropic(
                model=self.settings.anthropic_model,
                api_key=self.settings.anthropic_api_key.get_secret_value(),
                temperature=0.7,  # Higher temperature for creative goal generation
            )
        else:
            self.llm = llm

        self.structured_llm = self.llm.with_structured_output(ProposedGoal)

    async def generate_from_gap(self, gap: KnowledgeGap, curiosity_score: float) -> GeneratedGoal | None:
        """
        Generate an actionable research goal based on an identified Knowledge Gap.
        """
        logger.info(f"Generating goal from gap: {gap.domain}")
        
        system_prompt = (
            "You are an autonomous Research Goal Generator. Your task is to look at a "
            "detected knowledge gap in the system's database and propose a single, highly "
            "actionable research goal to close that gap."
        )

        user_content = (
            f"Knowledge Gap Domain: {gap.domain}\n"
            f"Description: {gap.description}\n"
            f"Importance: {gap.importance}\n\n"
            "Generate a research goal to resolve this gap."
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ]

        try:
            result: ProposedGoal = await self.structured_llm.ainvoke(messages)
            
            # Prevent duplicates (simple mock logic: usually requires embedding search)
            # We'll just create the goal record directly.
            
            goal = await self.goal_repo.create(
                gap_id=gap.id,
                title=result.title,
                description=result.description,
                status="generated",
                curiosity_score=curiosity_score
            )
            
            logger.info(f"Generated Goal: {goal.title} (Score: {curiosity_score:.2f})")
            return goal
            
        except Exception as e:
            logger.error(f"Failed to generate goal from gap: {e}")
            return None
