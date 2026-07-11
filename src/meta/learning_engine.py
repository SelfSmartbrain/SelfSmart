"""Learning Engine component."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.config.settings import get_settings
from src.db.repositories.learning_repo import LearningRepository

logger = logging.getLogger(__name__)


class ExtractedLearning(BaseModel):
    """A single learning extracted from a reflection."""
    
    pattern_type: str = Field(description="The category of the learning (e.g., 'context_management', 'error_handling').")
    description: str = Field(description="A clear description of the observed pattern or failure.")
    action_taken: str = Field(description="The proposed or successful action to address this pattern.")
    confidence: float = Field(description="Confidence in this learning (0.0 to 1.0).")


class LearningExtractionResponse(BaseModel):
    """List of extracted learnings."""
    
    learnings: list[ExtractedLearning]


class LearningEngine:
    """Converts reflection records into reusable strategies and policies."""

    def __init__(
        self,
        learning_repo: LearningRepository,
        llm: Any = None,
    ) -> None:
        self.repo = learning_repo
        self.settings = get_settings()
        
        if llm is None:
            from langchain_anthropic import ChatAnthropic
            self.llm = ChatAnthropic(
                model=self.settings.anthropic_model,
                api_key=self.settings.anthropic_api_key.get_secret_value(),
                temperature=0.2,
            )
        else:
            self.llm = llm

        self.structured_llm = self.llm.with_structured_output(LearningExtractionResponse)

    async def extract_learnings(
        self,
        session_id: UUID,
        reflections: list[dict[str, Any]],
        task_results: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Extract generic learnings from specific session reflections."""
        
        if not reflections:
            return []

        system_prompt = (
            "You are an expert AGI self-improvement system. Your goal is to analyze "
            "reflections from a recent agent session and extract generalizable learnings, "
            "patterns, and actionable policies.\n\n"
            "Focus on systemic issues, repeated failures, or highly successful strategies "
            "that can be applied to future tasks. Ignore transient or highly specific data."
        )

        user_content = (
            f"Task Results Summary:\n{task_results}\n\n"
            f"Reflections:\n{reflections}\n\n"
            "Extract the key learnings."
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ]

        try:
            result: LearningExtractionResponse = await self.structured_llm.ainvoke(messages)
            
            # Save learnings to database as LearningPatterns
            saved_learnings = []
            for learning in result.learnings:
                pattern = await self.repo.patterns.create(
                    pattern_type=learning.pattern_type,
                    description=learning.description,
                    source_sessions=[str(session_id)],
                    confidence=learning.confidence,
                    action_taken=learning.action_taken,
                )
                
                # Auto-generate policy for high confidence learnings
                if learning.confidence >= 0.8:
                    await self._generate_policy(pattern)
                    
                saved_learnings.append({
                    "id": str(pattern.id),
                    "pattern_type": pattern.pattern_type,
                    "description": pattern.description,
                    "action_taken": pattern.action_taken,
                })
                
            return saved_learnings
            
        except Exception as e:
            logger.error(f"Learning extraction failed: {e}")
            return []

    async def _generate_policy(self, pattern: Any) -> None:
        """Automatically promote a high-confidence pattern to an active policy."""
        # Simple promotion for now. In reality, LLM should format the condition/action.
        await self.repo.policies.create(
            name=f"Policy from {pattern.pattern_type}",
            description=f"Auto-generated from: {pattern.description}",
            condition=pattern.description,
            action=pattern.action_taken or "Apply learning",
            source_pattern_id=pattern.id,
            confidence=pattern.confidence,
            is_active=True,
        )
