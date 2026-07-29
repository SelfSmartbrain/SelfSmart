"""
src/agents/cognition_nodes.py

Purpose:
Contains the LangGraph node functions for the Phase 7.5 post-execution cognitive loop.
These nodes interface with the ServiceRegistry to execute deep meta-learning,
failure analysis, skill discovery, and self-improvement strategies.
"""

from __future__ import annotations

from typing import Any

from src.agents.state import AgentStateDict
from src.config.logging import get_logger
from src.core.service_registry import get_registry

logger = get_logger(__name__)


async def cognition_reflection_node(state: AgentStateDict) -> dict[str, Any]:
    """Reflect on the completed execution to extract structured insights."""
    logger.info("Executing cognition_reflection_node")
    registry = await get_registry()
    reflection_agent = registry.get("reflection_agent")

    # In a real run, we pass task_results and reflection_agent runs LLM analysis.
    # For now, we simulate the LLM extraction logic inside the node structure.

    task_results = state.get("task_results", {})
    total = len(task_results)
    successes = sum(1 for r in task_results.values() if r.get("status") == "completed")
    success_score = successes / max(total, 1)

    cognition_reflection = {
        "success_score": success_score,
        "quality_score": success_score * 0.9,
        "confidence_score": min(success_score + 0.1, 1.0),
        "completion_percentage": (successes / max(total, 1)) * 100,
        "reflection_summary": f"Completed {successes}/{total} tasks.",
    }

    reflections = list(state.get("cognition_reflections", []))
    reflections.append(cognition_reflection)

    return {"cognition_reflections": reflections}


async def failure_analysis_node(state: AgentStateDict) -> dict[str, Any]:
    """Detect and cluster recurring failure patterns."""
    logger.info("Executing failure_analysis_node")
    registry = await get_registry()
    failure_analyzer = registry.get("failure_analyzer")

    errors = state.get("errors", [])
    patterns: list[dict[str, Any]] = []

    if errors:
        error_groups: dict[str, list[dict[str, Any]]] = {}
        for err in errors:
            err_type = err.get("error_type", "unknown")
            error_groups.setdefault(err_type, []).append(err)

        for err_type, group in error_groups.items():
            patterns.append(
                {
                    "pattern_name": err_type,
                    "description": group[0].get("message", ""),
                    "frequency": len(group),
                    "severity": "high" if len(group) > 2 else "medium",
                    "recommended_fix": f"Address recurring {err_type} failures",
                }
            )

    return {"failure_patterns": patterns}


async def meta_learning_node(state: AgentStateDict) -> dict[str, Any]:
    """Learn from historical reflections, strategies, and failures."""
    logger.info("Executing meta_learning_node")
    registry = await get_registry()
    meta_engine = registry.get("meta_learning")

    failures = state.get("failure_patterns", [])
    recommendations = []

    for pattern in failures:
        if pattern.get("frequency", 0) > 1:
            recommendations.append(f"Recurring failure '{pattern.get('pattern_name')}' detected.")

    return {"optimization_recommendations": recommendations}


async def strategy_optimization_node(state: AgentStateDict) -> dict[str, Any]:
    """Optimize research strategies based on meta-learning."""
    logger.info("Executing strategy_optimization_node")
    registry = await get_registry()
    synthesizer = registry.get("strategy_synthesizer")

    selected = state.get("selected_strategy")
    reflections = state.get("cognition_reflections", [])

    best_strategy = selected
    if reflections and selected:
        avg_success = sum(r.get("success_score", 0) for r in reflections) / len(reflections)
        selected["computed_success_rate"] = avg_success
        best_strategy = selected

    return {"best_strategy": best_strategy}


async def skill_discovery_node(state: AgentStateDict) -> dict[str, Any]:
    """Discover reusable skills from repeated successful task workflows."""
    logger.info("Executing skill_discovery_node")
    registry = await get_registry()
    skill_engine = registry.get("skill_discovery")

    task_results = state.get("task_results", {})
    skills: list[dict[str, Any]] = []

    successful_tasks = [
        (tid, r) for tid, r in task_results.items() if r.get("status") == "completed"
    ]

    if len(successful_tasks) >= 2:
        skills.append(
            {
                "name": f"workflow_pattern_{state.get('goal', 'unknown')[:10]}",
                "description": f"Workflow extracted from {len(successful_tasks)} tasks",
                "skill_type": "workflow",
                "usage_count": 1,
                "success_rate": 1.0,
            }
        )

    return {"cognitive_skills": skills}


async def metrics_node(state: AgentStateDict) -> dict[str, Any]:
    """Record cognitive intelligence metrics."""
    logger.info("Executing metrics_node")
    registry = await get_registry()
    metrics_calculator = registry.get("cognitive_metrics")

    task_results = state.get("task_results", {})
    skills = state.get("cognitive_skills", [])

    total_tasks = len(task_results)
    successful = sum(1 for r in task_results.values() if r.get("status") == "completed")

    autonomy_score = min(successful / max(total_tasks, 1), 1.0)

    metrics = [
        {"metric_name": "autonomy_score", "metric_value": autonomy_score},
        {"metric_name": "skill_utilization", "metric_value": len(skills) * 0.1},
    ]

    return {
        "cognitive_metrics": metrics,
        "autonomy_score": autonomy_score,
    }


async def self_improvement_node(state: AgentStateDict) -> dict[str, Any]:
    """Evaluate system performance and generate improvement recommendations."""
    logger.info("Executing self_improvement_node")
    registry = await get_registry()
    improver = registry.get("self_improvement")

    recommendations = list(state.get("optimization_recommendations", []))
    autonomy = state.get("autonomy_score", 0.0)

    if autonomy < 0.5:
        recommendations.append("Low autonomy score detected.")

    return {"optimization_recommendations": recommendations}


# ---------------------------------------------------------------------------
# Phase 13: Cognitive Operating System Nodes (NOT YET WIRED - future phase)
# These nodes exist as forward-looking implementations but are not currently
# connected to the orchestrator graph. Wire them when Phase 13 is ready.
# ---------------------------------------------------------------------------


async def attention_allocation_node(state: AgentStateDict) -> dict[str, Any]:
    """Allocate cognitive attention to salient tasks and information."""
    logger.info("Executing attention_allocation_node")
    registry = await get_registry()
    attention_manager = registry.get("attention_manager")

    tasks = state.get("pending_tasks", [])
    attention_allocations = []

    # Simulate attention allocation based on priority and salience
    for task in tasks[:5]:  # Limit to top 5 tasks
        priority = task.get("priority", 0.5)
        salience = task.get("salience", 0.5)
        attention_score = (priority + salience) / 2

        if attention_score > 0.6:
            attention_allocations.append(
                {
                    "task_id": task.get("task_id"),
                    "attention_level": "high" if attention_score > 0.8 else "medium",
                    "allocated_amount": attention_score,
                    "processing_mode": "focused",
                }
            )

    return {"attention_allocations": attention_allocations}


async def memory_consolidation_node(state: AgentStateDict) -> dict[str, Any]:
    """Consolidate short-term memories into long-term storage."""
    logger.info("Executing memory_consolidation_node")
    registry = await get_registry()
    memory_fabric = registry.get("memory_fabric")

    recent_memories = state.get("recent_memories", [])
    consolidated_count = 0

    # Simulate memory consolidation
    for memory in recent_memories:
        importance = memory.get("importance", 0.5)
        if importance > 0.7:
            consolidated_count += 1

    return {
        "consolidated_memories": consolidated_count,
        "memory_links_created": consolidated_count * 2,
    }


async def deliberation_node(state: AgentStateDict) -> dict[str, Any]:
    """Perform System 2 deliberative reasoning on complex problems."""
    logger.info("Executing deliberation_node")
    registry = await get_registry()
    deliberation_engine = registry.get("deliberation_engine")

    complex_queries = state.get("complex_queries", [])
    deliberation_results = []

    for query in complex_queries:
        # Simulate deliberation process
        deliberation_results.append(
            {
                "query": query,
                "reasoning_mode": "system_2",
                "confidence": 0.75,
                "reasoning_steps": 4,
                "conclusion": f"Deliberated on: {query[:50]}...",
            }
        )

    return {"deliberation_results": deliberation_results}


async def society_planning_node(state: AgentStateDict) -> dict[str, Any]:
    """Plan multi-agent collaboration for complex tasks."""
    logger.info("Executing society_planning_node")
    registry = await get_registry()
    society_runtime = registry.get("society_runtime")

    collaboration_tasks = state.get("collaboration_tasks", [])
    society_plans = []

    for task in collaboration_tasks:
        # Simulate society planning
        society_plans.append(
            {
                "task_id": task.get("task_id"),
                "required_agents": task.get("required_capabilities", []),
                "collaboration_type": "cooperative",
                "estimated_duration": 300,
            }
        )

    return {"society_plans": society_plans}


async def identity_update_node(state: AgentStateDict) -> dict[str, Any]:
    """Update long-term identity based on experiences and learning."""
    logger.info("Executing identity_update_node")
    registry = await get_registry()
    identity_engine = registry.get("identity_engine")

    experiences = state.get("experiences", [])
    identity_updates = []

    # Simulate identity updates based on experiences
    if len(experiences) > 5:
        identity_updates.append(
            {
                "update_type": "skill_improvement",
                "skill": "reasoning",
                "delta": 0.05,
            }
        )

    return {"identity_updates": identity_updates}


async def program_execution_node(state: AgentStateDict) -> dict[str, Any]:
    """Execute long-running research programs."""
    logger.info("Executing program_execution_node")
    registry = await get_registry()
    program_scheduler = registry.get("program_scheduler")

    active_programs = state.get("active_programs", [])
    execution_results = []

    for program in active_programs:
        # Simulate program execution
        execution_results.append(
            {
                "program_id": program.get("program_id"),
                "status": "in_progress",
                "progress_increment": 0.1,
                "insights_generated": 1,
            }
        )

    return {"program_execution_results": execution_results}
