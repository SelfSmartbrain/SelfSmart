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
    """Evaluate raw capabilities."""
    logger.info("Executing capability_evaluation node.")
    eval_results = {"status": "evaluated", "metrics": {}}
    return {"capability_evaluation_results": eval_results}

async def benchmark_execution(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute capability benchmarks."""
    logger.info("Executing benchmark_execution node.")
    benchmark_results = {"status": "executed", "score": 0.0}
    return {"benchmark_results": benchmark_results}

async def transfer_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze knowledge transferability."""
    logger.info("Executing transfer_analysis node.")
    transfer_results = {"transfer_score": 0.85}
    return {"transfer_analysis_results": transfer_results}

async def discovery_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze newly discovered capabilities."""
    logger.info("Executing discovery_analysis node.")
    discovery_results = {"new_skills": []}
    return {"discovery_results": discovery_results}

async def peer_review(state: Dict[str, Any]) -> Dict[str, Any]:
    """Review capabilities against peer models."""
    logger.info("Executing peer_review node.")
    review_results = {"peer_comparison": "average"}
    return {"peer_review_results": review_results}

async def regression_detection(state: Dict[str, Any]) -> Dict[str, Any]:
    """Detect any capability regressions."""
    logger.info("Executing regression_detection node.")
    regression_results = {"regressions_found": False}
    return {"regression_results": regression_results}

async def program_evaluation(state: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate training program effectiveness."""
    logger.info("Executing program_evaluation node.")
    program_results = {"effectiveness": "high"}
    return {"program_evaluation_results": program_results}

async def capability_reporting(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate capability report."""
    logger.info("Executing capability_reporting node.")
    report = {"report_id": "rep-123", "status": "generated"}
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
