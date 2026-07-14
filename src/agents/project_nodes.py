from __future__ import annotations

import json
import logging
from typing import Any, Dict, List
from src.core.service_registry import get_registry

logger = logging.getLogger(__name__)


def _parse_json_response(content: Any, fallback: Any) -> Any:
    text = str(content)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start_obj = text.find("{")
        end_obj = text.rfind("}") + 1
        start_arr = text.find("[")
        end_arr = text.rfind("]") + 1
        candidates = []
        if start_obj >= 0 and end_obj > start_obj:
            candidates.append(text[start_obj:end_obj])
        if start_arr >= 0 and end_arr > start_arr:
            candidates.append(text[start_arr:end_arr])
        for candidate in candidates:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
    return fallback


async def _llm_json(system: str, prompt: str, fallback: Any) -> Any:
    try:
        registry = await get_registry()
        llm = registry.get("llm")
        if llm:
            from langchain_core.messages import HumanMessage, SystemMessage

            response = await llm.ainvoke(
                [
                    SystemMessage(content=system),
                    HumanMessage(content=prompt),
                ]
            )
            return _parse_json_response(response.content, fallback)
    except Exception as e:
        logger.warning("Project node LLM call failed: %s", e)
    return fallback


async def environment_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the current environment for trends, risks, and opportunities."""
    fallback = {
        "environment_analysis": {
            "trends": [],
            "risks": [],
            "opportunities": [],
            "summary": "No environment analysis available"
        }
    }
    system = "You are an expert business analyst specializing in environmental scanning. Return only a JSON object."
    prompt = f"""
Analyze the current business environment based on the following state:
{json.dumps(state, default=str)[:4000]}

Return a JSON object with the following structure:
{{
  "trends": ["list of key trends"],
  "risks": ["list of key risks"],
  "opportunities": ["list of key opportunities"],
  "summary": "brief summary of the environmental analysis"
}}
"""
    result = await _llm_json(system, prompt, fallback)
    # Ensure the result has the expected structure
    if not isinstance(result, dict) or "environment_analysis" not in result:
        return fallback
    return result


async def opportunity_detection(state: Dict[str, Any]) -> Dict[str, Any]:
    """Detect specific business opportunities from the environment analysis."""
    fallback = {
        "opportunities": [
            {
                "id": "opp1",
                "title": "Generic Opportunity",
                "description": "Opportunity detected via fallback",
                "priority": "medium",
                "estimated_impact": "unknown"
            }
        ]
    }
    system = "You are an opportunity identification expert. Return only a JSON object."
    prompt = f"""
Based on the following state, particularly the environment analysis, identify 2-4 specific business opportunities:
{json.dumps(state, default=str)[:4000]}

Return a JSON object with the following structure:
{{
  "opportunities": [
    {{
      "id": "unique identifier string",
      "title": "short title",
      "description": "detailed description",
      "priority": "high|medium|low",
      "estimated_impact": "description of potential impact"
    }}
  ]
}}
"""
    result = await _llm_json(system, prompt, fallback)
    if not isinstance(result, dict) or "opportunities" not in result:
        return fallback
    # Ensure each opportunity has an ID
    for opp in result.get("opportunities", []):
        if not opp.get("id"):
            opp["id"] = f"opp_{hash(opp.get('title', '')) % 10000}"
    return result


async def project_creation(state: Dict[str, Any]) -> Dict[str, Any]:
    """Create project proposals from detected opportunities."""
    fallback = {
        "projects": [
            {
                "id": "proj1",
                "name": "Default Project",
                "description": "Project created from fallback",
                "opportunity_id": "opp1",
                "status": "proposed"
            }
        ]
    }
    system = "You are a project initiation expert. Return only a JSON object."
    prompt = f"""
Based on the following state, particularly the opportunities identified, create project proposals:
{json.dumps(state, default=str)[:4000]}

Return a JSON object with the following structure:
{{
  "projects": [
    {{
      "id": "unique identifier string",
      "name": "project name",
      "description": "project description",
      "opportunity_id": "id of the opportunity this project addresses",
      "status": "proposed|planning|on_hold"
    }}
  ]
}}
"""
    result = await _llm_json(system, prompt, fallback)
    if not isinstance(result, dict) or "projects" not in result:
        return fallback
    # Ensure each project has an ID
    for proj in result.get("projects", []):
        if not proj.get("id"):
            proj["id"] = f"proj_{hash(proj.get('name', '')) % 10000}"
    return result


async def task_decomposition(state: Dict[str, Any]) -> Dict[str, Any]:
    """Break down projects into actionable tasks."""
    fallback = {
        "tasks": [
            {
                "id": "task1",
                "project_id": "proj1",
                "title": "Default Task",
                "description": "Task created from fallback",
                "estimated_effort": "unknown",
                "dependencies": []
            }
        ]
    }
    system = "You are a project planning expert specializing in work breakdown. Return only a JSON object."
    prompt = f"""
Based on the following state, particularly the projects defined, break down each project into specific, actionable tasks:
{json.dumps(state, default=str)[:4000]}

Return a JSON object with the following structure:
{{
  "tasks": [
    {{
      "id": "unique identifier string",
      "project_id": "id of the parent project",
      "title": "short task title",
      "description": "detailed task description",
      "estimated_effort": "e.g., '2 days', '5 hours'",
      "dependencies": ["list of task IDs that must be completed first"]
    }}
  ]
}}
"""
    result = await _llm_json(simple, prompt, fallback)
    if not isinstance(result, dict) or "tasks" not in result:
        return fallback
    # Ensure each task has an ID
    for task in result.get("tasks", []):
        if not task.get("id"):
            task["id"] = f"task_{hash(task.get('title', '')) % 10000}"
    return result


async def resource_allocation(state: Dict[str, Any]) -> Dict[str, Any]:
    """Assign resources (people, budget, tools) to tasks."""
    fallback = {
        "allocations": [
            {
                "task_id": "task1",
                "resources": {
                    "personnel": ["unassigned"],
                    "budget": 0,
                    "tools": []
                }
            }
        ]
    }
    system = "You are a resource management expert. Return only a JSON object."
    prompt = f"""
Based on the following state, particularly the tasks that need to be performed, allocate appropriate resources:
{json.dumps(state, default=str)[:4000]}

Return a JSON object with the following structure:
{{
  "allocations": [
    {{
      "task_id": "id of the task",
      "resources": {{
        "personnel": ["list of person names or roles"],
        "budget": number (in currency units),
        "tools": ["list of required tools or software"]
      }}
    }}
  ]
}}
"""
    result = await _llm_json(system, prompt, fallback)
    if not isinstance(result, dict) or "allocations" not in result:
        return fallback
    return result


async def execution(state: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate execution of tasks (in a real system, this would trigger actual work)."""
    # In a real implementation, this would interface with a task execution system
    # For now, we'll mark tasks as completed based on some simple logic
    fallback = {
        "execution_results": [
            {
                "task_id": "task1",
                "status": "completed",
                "actual_effort": "unknown",
                "notes": "Execution simulated via fallback"
            }
        ]
    }
    system = "You are a project execution simulator. Return only a JSON object."
    prompt = f"""
Based on the following state, particularly the tasks and their resource allocations, simulate the execution of tasks:
{json.dumps(state, default=str)[:4000]}

For each task, determine if it would succeed or fail based on the resources and dependencies.
Return a JSON object with the following structure:
{{
  "execution_results": [
    {{
      "task_id": "id of the task",
      "status": "completed|failed|in_progress",
      "actual_effort": "actual time taken (e.g., '1.5 days')",
      "notes": "any observations about the execution"
    }}
  ]
}}
"""
    result = await _llm_json(system, prompt, fallback)
    if not isinstance(result, dict) or "execution_results" not in result:
        return fallback
    return result


async def checkpointing(state: Dict[str, Any]) -> Dict[str, Any]:
    """Create checkpoints to save progress and enable recovery."""
    fallback = {
        "checkpoint": {
            "id": "cp1",
            "timestamp": "unknown",
            "saved_state": {},
            "description": "Default checkpoint"
        }
    }
    system = "You are a project management expert. Return only a JSON object."
    prompt = f"""
Based on the following state, create a checkpoint that captures the current progress:
{json.dumps(state, default=str)[:4000]}

Return a JSON object with the following structure:
{{
  "checkpoint": {{
    "id": "unique identifier string",
    "timestamp": "ISO 8601 timestamp string",
    "saved_state": {{}},
    "description": "description of what this checkpoint saves"
  }}
}}
"""
    result = await _llm_json(system, prompt, fallback)
    if not isinstance(result, dict) or "checkpoint" not in result:
        return fallback
    # Ensure the checkpoint has an ID and timestamp
    if not result["checkpoint"].get("id"):
        result["checkpoint"]["id"] = f"cp_{hash(str(result)) % 10000}"
    if not result["checkpoint"].get("timestamp"):
        from datetime import datetime
        result["checkpoint"]["timestamp"] = datetime.now().isoformat()
    return result


async def failure_recovery(state: Dict[str, Any]) -> Dict[str, Any]:
    """Recover from failures using checkpoints and alternative approaches."""
    fallback = {
        "recovery_actions": [
            {
                "action": "restart_from_last_checkpoint",
                "details": "Recovered via fallback mechanism",
                "success": False
            }
        ]
    }
    system = "You are a disaster recovery expert. Return only a JSON object."
    prompt = f"""
Based on the following state, particularly any failed tasks or errors, determine appropriate recovery actions:
{json.dumps(state, default=str)[:4000]}

Return a JSON object with the following structure:
{{
  "recovery_actions": [
    {{
      "action": "description of the recovery action",
      "details": "specifics of how to perform the action",
      "success": true/false (likelihood of success)
    }}
  ]
}}
"""
    result = await _llm_json(system, prompt, fallback)
    if not isinstance(result, dict) or "recovery_actions" not in result:
        return fallback
    return result


async def impact_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the impact of completed projects or initiatives."""
    fallback = {
        "impact": {
            "score": 50,
            "details": "Impact analysis via fallback - moderate impact assumed"
        }
    }
    system = "You are an impact analysis expert. Return only a JSON object."
    prompt = f"""
Based on the following state, particularly completed tasks and projects, analyze the business impact:
{json.dumps(state, default=str)[:4000]}

Return a JSON object with the following structure:
{{
  "impact": {{
    "score": integer (0-100 representing impact magnitude),
    "details": "explanation of the impact assessment"
  }}
}}
"""
    result = await _llm_json(system, prompt, fallback)
    if not isinstance(result, dict) or "impact" not in result:
        return fallback
    # Ensure score is an integer between 0 and 100
    score = result["impact"].get("score", 50)
    if not isinstance(score, int) or score < 0 or score > 100:
        result["impact"]["score"] = 50
    return result


async def project_completion(state: Dict[str, Any]) -> Dict[str, Any]:
    """Mark projects as complete and capture lessons learned."""
    fallback = {
        "completed_projects": [],
        "lessons_learned": ["No lessons learned - fallback used"]
    }
    system = "You are a project closure expert. Return only a JSON object."
    prompt = f"""
Based on the following state, particularly finished projects and their outcomes, determine which projects are complete and capture lessons learned:
{json.dumps(state, default=str)[:4000]}

Return a JSON object with the following structure:
{{
  "completed_projects": [
    {{
      "project_id": "id of the completed project",
      "completion_date": "ISO 8601 timestamp string",
      "final_status": "success|partial_success|failure"
    }}
  ],
  "lessons_learned": ["list of lessons learned from the projects"]
}}
"""
    result = await _llm_json(system, prompt, fallback)
    if not isinstance(result, dict):
        return fallback
    # Ensure we have the expected keys
    if "completed_projects" not in result:
        result["completed_projects"] = []
    if "lessons_learned" not in result:
        result["lessons_learned"] = ["No lessons learned"]
    return result


# Node assignments for the orchestrator
environment_analysis_node = environment_analysis
opportunity_detection_node = opportunity_detection
project_creation_node = project_creation
task_decomposition_node = task_decomposition
resource_allocation_node = resource_allocation
execution_node = execution
checkpointing_node = checkpointing
failure_recovery_node = failure_recovery
impact_analysis_node = impact_analysis
project_completion_node = project_completion