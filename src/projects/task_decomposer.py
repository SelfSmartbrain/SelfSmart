from __future__ import annotations
import uuid
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)

class ProjectTask(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    milestone_id: uuid.UUID
    title: str
    description: str
    status: str = "todo"
    dependencies: List[uuid.UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TaskDecomposer(BaseModel):
    model_config = {"from_attributes": True}
    
    def __init__(self, **data):
        super().__init__(**data)
        settings = get_settings()
        llm_kwargs = {
            "model": settings.anthropic_model,
            "api_key": settings.anthropic_api_key.get_secret_value(),
            "temperature": 0.3,
            "max_tokens": 4096,
        }
        if settings.anthropic_base_url:
            llm_kwargs["base_url"] = settings.anthropic_base_url
        self.llm = ChatAnthropic(**llm_kwargs)
    
    async def decompose_milestone(self, milestone_id: uuid.UUID, description: str) -> List[ProjectTask]:
        """
        Decompose a milestone into executable tasks using LLM analysis.
        
        The LLM analyzes the milestone description and generates a structured
        list of tasks with appropriate dependencies and ordering.
        """
        logger.info(f"Decomposing milestone {milestone_id} into tasks using LLM")
        
        system_prompt = """You are an expert project manager and software architect. Your task is to decompose project milestones into concrete, executable tasks.

For each milestone description provided:
1. Break it down into 3-8 specific, actionable tasks
2. Order tasks logically (dependencies should flow from earlier to later tasks)
3. Each task should have a clear title and detailed description
4. Identify dependencies between tasks (task B depends on task A if A must complete before B starts)

Return your response as a JSON array with this exact structure:
[
  {
    "title": "Clear, actionable task title",
    "description": "Detailed description of what needs to be done, including acceptance criteria",
    "dependencies": ["index of task this depends on (0-based)"]
  }
]

Rules:
- Dependencies should be an array of integers representing task indices
- If a task has no dependencies, use an empty array []
- Tasks should be ordered so dependencies appear before dependent tasks
- Each task should be independently verifiable
- Avoid overly broad tasks; be specific and concrete"""

        user_prompt = f"""Decompose the following milestone into executable tasks:

Milestone Description:
{description}

Provide the task breakdown as a JSON array following the system prompt structure."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            response_text = response.content.strip()
            
            # Extract JSON from response (handle potential markdown code blocks)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            tasks_data = json.loads(response_text)
            
            # Convert to ProjectTask objects
            tasks = []
            task_map = {}  # Maps index to UUID for dependency resolution
            
            for idx, task_data in enumerate(tasks_data):
                task_id = uuid.uuid4()
                task_map[idx] = task_id
                
                # Convert dependency indices to UUIDs
                dependency_uuids = []
                for dep_idx in task_data.get("dependencies", []):
                    if dep_idx in task_map:
                        dependency_uuids.append(task_map[dep_idx])
                
                task = ProjectTask(
                    milestone_id=milestone_id,
                    title=task_data["title"],
                    description=task_data["description"],
                    dependencies=dependency_uuids
                )
                tasks.append(task)
            
            logger.info(f"Successfully decomposed milestone into {len(tasks)} tasks")
            return tasks
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response text: {response_text}")
            # Fallback to generic task structure
            return [
                ProjectTask(
                    milestone_id=milestone_id,
                    title="Analyze milestone requirements",
                    description=f"Analyze and clarify requirements for: {description}"
                ),
                ProjectTask(
                    milestone_id=milestone_id,
                    title="Implement milestone",
                    description=f"Implement the core functionality for: {description}",
                    dependencies=[tasks[0].id] if tasks else []
                )
            ]
        except Exception as e:
            logger.error(f"Error during task decomposition: {e}")
            raise
