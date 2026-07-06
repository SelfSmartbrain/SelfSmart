from __future__ import annotations

import json
from typing import Any, Dict

from src.config.logging import get_logger
from src.core.service_registry import get_registry

logger = get_logger(__name__)


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
        logger.warning("Capability node LLM call failed", error=str(e))
    return fallback

async def capability_evaluation(state: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate system capabilities based on task results and skill inventory."""
    logger.info("Executing capability_evaluation node.")
    task_results = state.get("task_results", {})
    cognitive_skills = state.get("cognitive_skills", [])

    total = len(task_results)
    successes = sum(1 for r in task_results.values() if r.get("status") == "completed")
    success_rate = successes / max(total, 1)

    metrics = {
        "task_success_rate": success_rate,
        "total_tasks_evaluated": total,
        "skill_count": len(cognitive_skills),
        "capability_score": min(success_rate + len(cognitive_skills) * 0.05, 1.0),
    }

    llm_eval = await _llm_json(
        system="You are a capability evaluator. Assess the system capabilities given these metrics. Return JSON.",
        prompt=f"Metrics: {json.dumps(metrics)}\nSkills: {json.dumps(cognitive_skills[:5], default=str)}",
        fallback=None,
    )
    if isinstance(llm_eval, dict):
        metrics.update(llm_eval)

    return {"capability_evaluation_results": {"status": "evaluated", "metrics": metrics}}


async def benchmark_execution(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute capability benchmarks by scoring recent task performance."""
    logger.info("Executing benchmark_execution node.")
    task_results = state.get("task_results", {})

    total = len(task_results)
    successes = sum(1 for r in task_results.values() if r.get("status") == "completed")
    avg_duration = 0.0
    durations = [r.get("duration_ms", 0) for r in task_results.values() if r.get("duration_ms")]
    if durations:
        avg_duration = sum(durations) / len(durations)

    benchmark_results = {
        "status": "executed",
        "score": successes / max(total, 1),
        "avg_duration_ms": avg_duration,
        "tasks_benchmarked": total,
    }
    return {"benchmark_results": benchmark_results}


async def transfer_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze knowledge transferability across domains."""
    logger.info("Executing transfer_analysis node.")
    learnings = state.get("learnings", [])
    cognitive_skills = state.get("cognitive_skills", [])

    # Estimate transfer potential from skill diversity
    unique_domains = set()
    for skill in cognitive_skills:
        unique_domains.add(skill.get("skill_type", "general"))

    transfer_score = min(len(unique_domains) * 0.2 + len(learnings) * 0.05, 1.0)

    transfer_results = {
        "transfer_score": transfer_score,
        "unique_domains": list(unique_domains),
        "learning_count": len(learnings),
    }
    return {"transfer_analysis_results": transfer_results}


async def discovery_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze newly discovered capabilities from recent executions."""
    logger.info("Executing discovery_analysis node.")
    cognitive_skills = state.get("cognitive_skills", [])
    task_results = state.get("task_results", {})

    new_skills = []
    for skill in cognitive_skills:
        if skill.get("usage_count", 0) <= 1:
            new_skills.append({
                "name": skill.get("name", "unknown"),
                "type": skill.get("skill_type", "unknown"),
                "potential": skill.get("success_rate", 0.0),
            })

    discovery_results = {
        "new_skills": new_skills,
        "discovery_count": len(new_skills),
        "total_capabilities": len(cognitive_skills),
    }
    return {"discovery_results": discovery_results}


async def peer_review(state: Dict[str, Any]) -> Dict[str, Any]:
    """Review capabilities by comparing current vs historical performance."""
    logger.info("Executing peer_review node.")
    autonomy_score = state.get("autonomy_score", 0.0)
    cognition_reflections = state.get("cognition_reflections", [])

    if cognition_reflections:
        avg_quality = sum(r.get("quality_score", 0) for r in cognition_reflections) / len(cognition_reflections)
    else:
        avg_quality = 0.0

    if avg_quality >= 0.8:
        comparison = "above_average"
    elif avg_quality >= 0.5:
        comparison = "average"
    else:
        comparison = "below_average"

    review_results = {
        "peer_comparison": comparison,
        "autonomy_score": autonomy_score,
        "avg_quality_score": avg_quality,
        "reflections_reviewed": len(cognition_reflections),
    }
    return {"peer_review_results": review_results}


async def regression_detection(state: Dict[str, Any]) -> Dict[str, Any]:
    """Detect any capability regressions by comparing error patterns."""
    logger.info("Executing regression_detection node.")
    failure_patterns = state.get("failure_patterns", [])
    errors = state.get("errors", [])

    regressions = []
    for pattern in failure_patterns:
        if pattern.get("frequency", 0) > 2 and pattern.get("severity") == "high":
            regressions.append({
                "pattern": pattern.get("pattern_name", "unknown"),
                "frequency": pattern.get("frequency", 0),
                "recommendation": pattern.get("recommended_fix", "Investigate recurring failure"),
            })

    regression_results = {
        "regressions_found": len(regressions) > 0,
        "regression_count": len(regressions),
        "regressions": regressions,
        "total_error_count": len(errors),
    }
    return {"regression_results": regression_results}


async def program_evaluation(state: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate overall program effectiveness from accumulated metrics."""
    logger.info("Executing program_evaluation node.")
    cognitive_metrics = state.get("cognitive_metrics", [])
    optimization_recommendations = state.get("optimization_recommendations", [])

    metric_summary = {}
    for metric in cognitive_metrics:
        name = metric.get("metric_name", "unknown")
        value = metric.get("metric_value", 0.0)
        metric_summary[name] = value

    effectiveness = "high" if metric_summary.get("autonomy_score", 0) >= 0.7 else \
                    "medium" if metric_summary.get("autonomy_score", 0) >= 0.4 else "low"

    program_results = {
        "effectiveness": effectiveness,
        "metrics": metric_summary,
        "pending_recommendations": len(optimization_recommendations),
    }
    return {"program_evaluation_results": program_results}


async def capability_reporting(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a comprehensive capability report from all evaluation data."""
    logger.info("Executing capability_reporting node.")

    report = {
        "status": "generated",
        "evaluation": state.get("capability_evaluation_results", {}),
        "benchmarks": state.get("benchmark_results", {}),
        "transfer": state.get("transfer_analysis_results", {}),
        "discoveries": state.get("discovery_results", {}),
        "peer_review": state.get("peer_review_results", {}),
        "regressions": state.get("regression_results", {}),
        "program": state.get("program_evaluation_results", {}),
    }

    # Try LLM summary
    summary = await _llm_json(
        system="Summarize this capability report into a concise JSON with 'summary', 'strengths', 'weaknesses', and 'recommendations' keys.",
        prompt=json.dumps(report, default=str)[:4000],
        fallback=None,
    )
    if isinstance(summary, dict):
        report["llm_summary"] = summary

    return {"capability_report": report}


async def capability_gap_detection_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Executing capability_gap_detection_node.")
    failures = state.get("failure_patterns", [])
    errors = state.get("errors", [])
    fallback = [
        {
            "capability": item.get("pattern_name", "unknown"),
            "description": item.get("description", ""),
            "severity": item.get("severity", "medium"),
        }
        for item in failures
        if isinstance(item, dict)
    ]
    if not fallback:
        fallback = [
            {
                "capability": error.get("agent_type", "execution"),
                "description": error.get("message", ""),
                "severity": "medium",
            }
            for error in errors
            if isinstance(error, dict)
        ]
    gaps = await _llm_json(
        "You identify missing agent capabilities. Return only a JSON array.",
        f"Detect capability gaps from state:\n{json.dumps(state, default=str)[:4000]}",
        fallback,
    )
    return {"capability_gaps": gaps if isinstance(gaps, list) else fallback}


async def tool_specification_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Executing tool_specification_node.")
    gaps = state.get("capability_gaps", [])
    fallback = [
        {
            "name": f"{gap.get('capability', 'capability')}_tool",
            "purpose": gap.get("description", "Address capability gap"),
            "inputs": ["context"],
            "outputs": ["result"],
        }
        for gap in gaps
        if isinstance(gap, dict)
    ]
    specs = await _llm_json(
        "You write safe tool specifications. Return only a JSON array.",
        f"Create tool specifications for gaps:\n{json.dumps(gaps, default=str)[:4000]}",
        fallback,
    )
    return {"tool_specifications": specs if isinstance(specs, list) else fallback}


async def tool_generation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Executing tool_generation_node.")
    specs = state.get("tool_specifications", [])
    fallback = [
        {
            "name": spec.get("name", "generated_tool"),
            "status": "spec_only",
            "specification": spec,
        }
        for spec in specs
        if isinstance(spec, dict)
    ]
    tools = await _llm_json(
        "You design implementation plans for tools. Return only a JSON array.",
        f"Generate safe tool plans from specs:\n{json.dumps(specs, default=str)[:4000]}",
        fallback,
    )
    return {"generated_tools": tools if isinstance(tools, list) else fallback}


async def tool_validation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Executing tool_validation_node.")
    tools = state.get("generated_tools", [])
    fallback = [
        {
            "name": tool.get("name", "generated_tool"),
            "valid": bool(tool.get("name")),
            "issues": [] if tool.get("name") else ["missing name"],
        }
        for tool in tools
        if isinstance(tool, dict)
    ]
    results = await _llm_json(
        "You validate generated tool plans for safety and usefulness. Return only a JSON array.",
        f"Validate generated tools:\n{json.dumps(tools, default=str)[:4000]}",
        fallback,
    )
    return {"tool_validation_results": results if isinstance(results, list) else fallback}


async def tool_registration_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Executing tool_registration_node.")
    tools = state.get("generated_tools", [])
    validations = state.get("tool_validation_results", [])
    valid_names = {
        item.get("name")
        for item in validations
        if isinstance(item, dict) and item.get("valid", False)
    }
    registered = [
        {**tool, "registered": True}
        for tool in tools
        if isinstance(tool, dict) and tool.get("name") in valid_names
    ]
    return {"registered_tools": registered}


async def tool_evolution_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Executing tool_evolution_node.")
    registered = state.get("registered_tools", [])
    fallback = [
        {
            "name": tool.get("name", "registered_tool"),
            "next_action": "benchmark",
            "status": "ready",
        }
        for tool in registered
        if isinstance(tool, dict)
    ]
    evolution_results = await _llm_json(
        "You recommend next evolution steps for registered tools. Return only a JSON array.",
        f"Recommend tool evolution steps:\n{json.dumps(registered, default=str)[:4000]}",
        fallback,
    )
    return {
        "tool_evolution_results": evolution_results
        if isinstance(evolution_results, list)
        else fallback
    }


capability_evaluation_node = capability_evaluation
benchmark_execution_node = benchmark_execution
transfer_analysis_node = transfer_analysis
discovery_analysis_node = discovery_analysis
peer_review_node = peer_review
regression_detection_node = regression_detection
program_evaluation_node = program_evaluation
capability_reporting_node = capability_reporting
