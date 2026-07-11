"""Task Classifier component."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.config.settings import get_settings
from src.db.enums import TaskType

logger = logging.getLogger(__name__)


class TaskClassification(BaseModel):
    """Structured output for task classification."""
    
    task_type: TaskType = Field(
        description="The primary category of the task. Must be one of the allowed TaskType values."
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0.",
        ge=0.0,
        le=1.0,
    )
    subtypes: list[str] = Field(
        description="Optional list of more specific task subtypes or tags (e.g., ['python', 'refactoring'])."
    )
    reasoning: str = Field(
        description="Brief explanation of why this classification was chosen."
    )


class TaskClassifier:
    """Uses LLM to classify tasks into predefined categories."""

    def __init__(self, llm: Any = None) -> None:
        self.settings = get_settings()
        if llm is None:
            # Lazy import to avoid circular dependencies if needed
            from langchain_anthropic import ChatAnthropic
            self.llm = ChatAnthropic(
                model=self.settings.anthropic_model,
                api_key=self.settings.anthropic_api_key.get_secret_value(),
                temperature=0.0,
            )
        else:
            self.llm = llm

        # Use structured output
        self.structured_llm = self.llm.with_structured_output(TaskClassification)

    async def classify(self, task_description: str, context: str | None = None) -> dict[str, Any]:
        """Classify a task description into a TaskType."""
        
        system_prompt = (
            "You are an expert AI task classifier. Your job is to analyze a task description "
            "and categorize it into exactly one of the following primary types:\n\n"
        )
        
        for task_type in TaskType:
            system_prompt += f"- {task_type.value}\n"
            
        system_prompt += (
            "\nAnalyze the task carefully and provide the classification, a confidence score, "
            "relevant subtypes/tags, and a brief reasoning."
        )

        user_content = f"Task Description:\n{task_description}\n"
        if context:
            user_content += f"\nAdditional Context:\n{context}\n"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ]

        try:
            result: TaskClassification = await self.structured_llm.ainvoke(messages)
            return result.model_dump()
        except Exception as e:
            logger.error(f"Task classification failed: {e}")
            # Fallback
            return {
                "task_type": TaskType.MULTI_STEP_REASONING.value,
                "confidence": 0.1,
                "subtypes": ["fallback"],
                "reasoning": f"Classification failed: {e}",
            }
