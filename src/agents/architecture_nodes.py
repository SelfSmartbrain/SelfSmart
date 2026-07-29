from __future__ import annotations

import json
import logging
from typing import Dict, Any, List, Optional
from src.config.logging import get_logger
from src.core.service_registry import get_registry
from typing_extensions import TypedDict

logger = get_logger(__name__)


class AgentStateDict(TypedDict, total=False):
    architecture_id: str
    version: str
    components: List[Dict[str, Any]]
    dependencies: List[Dict[str, Any]]
    bottlenecks: List[Dict[str, Any]]
    hypotheses: List[Dict[str, Any]]
    candidates: List[Dict[str, Any]]
    benchmarks: List[Dict[str, Any]]
    reports: List[Dict[str, Any]]
    status: str


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
        logger.warning("Architecture node LLM call failed", error=str(e))
    return fallback


async def architecture_analysis(state: AgentStateDict) -> AgentStateDict:
    logger.info("Running architecture_analysis node")
    components = state.get("components", [])
    dependencies = state.get("dependencies", [])
    fallback = {
        "summary": "Architecture analysis completed with local state only.",
        "component_count": len(components),
        "dependency_count": len(dependencies),
    }
    analysis = await _llm_json(
        "You are an architecture analyst. Return a JSON object.",
        "Analyze architecture for this state:\n"
        f"{json.dumps({'goal': state.get('goal'), 'components': components, 'dependencies': dependencies}, default=str)[:4000]}",
        fallback,
    )
    return {"status": "architecture_analysis_complete", "architecture_analysis": analysis}


async def dependency_analysis(state: AgentStateDict) -> AgentStateDict:
    logger.info("Running dependency_analysis node")
    dependencies = state.get("dependencies", [])
    fallback = {"dependencies": dependencies, "risk_count": 0}
    analysis = await _llm_json(
        "You analyze software dependencies. Return a JSON object with dependencies and risks.",
        f"Analyze dependency health:\n{json.dumps(dependencies, default=str)[:4000]}",
        fallback,
    )
    return {"status": "dependency_analysis_complete", "dependency_analysis": analysis}


async def component_analysis(state: AgentStateDict) -> AgentStateDict:
    logger.info("Running component_analysis node")
    components = state.get("components", [])
    fallback = {"components": components, "component_count": len(components)}
    analysis = await _llm_json(
        "You analyze system components. Return a JSON object.",
        f"Analyze these components:\n{json.dumps(components, default=str)[:4000]}",
        fallback,
    )
    return {"status": "component_analysis_complete", "component_analysis": analysis}


async def bottleneck_detection(state: AgentStateDict) -> AgentStateDict:
    logger.info("Running bottleneck_detection node")
    fallback = state.get("bottlenecks", [])
    bottlenecks = await _llm_json(
        "You detect architecture bottlenecks. Return only a JSON array.",
        f"Find bottlenecks in this state:\n{json.dumps(dict(state), default=str)[:4000]}",
        fallback,
    )
    return {"status": "bottleneck_detection_complete", "bottlenecks": bottlenecks}


async def hypothesis_generation(state: AgentStateDict) -> AgentStateDict:
    logger.info("Running hypothesis_generation node")
    fallback = state.get("hypotheses", [])
    hypotheses = await _llm_json(
        "You generate architecture improvement hypotheses. Return only a JSON array.",
        f"Generate hypotheses from architecture state:\n{json.dumps(dict(state), default=str)[:4000]}",
        fallback,
    )
    return {"status": "hypothesis_generation_complete", "hypotheses": hypotheses}


async def candidate_generation(state: AgentStateDict) -> AgentStateDict:
    logger.info("Running candidate_generation node")
    fallback = state.get("candidates", [])
    candidates = await _llm_json(
        "You generate architecture candidates. Return only a JSON array.",
        f"Generate candidates from hypotheses:\n{json.dumps(state.get('hypotheses', []), default=str)[:4000]}",
        fallback,
    )
    return {"status": "candidate_generation_complete", "candidates": candidates}


async def sandbox_benchmarking(state: AgentStateDict) -> AgentStateDict:
    logger.info("Running sandbox_benchmarking node")
    candidates = state.get("candidates", [])
    fallback = [
        {"candidate_id": candidate.get("id", index), "score": 0.0, "status": "not_executed"}
        for index, candidate in enumerate(candidates, start=1)
        if isinstance(candidate, dict)
    ]
    benchmarks = await _llm_json(
        "You estimate architecture benchmark outcomes. Return only a JSON array.",
        f"Benchmark these candidates conceptually:\n{json.dumps(candidates, default=str)[:4000]}",
        fallback,
    )
    return {"status": "sandbox_benchmarking_complete", "benchmarks": benchmarks}


async def benchmark_reporting(state: AgentStateDict) -> AgentStateDict:
    logger.info("Running benchmark_reporting node")
    benchmarks = state.get("benchmarks", [])
    fallback = {
        "benchmark_count": len(benchmarks),
        "best_candidate": (
            max(benchmarks, key=lambda item: item.get("score", 0.0), default=None)
            if all(isinstance(item, dict) for item in benchmarks)
            else None
        ),
    }
    report = await _llm_json(
        "You summarize architecture benchmark results. Return a JSON object.",
        f"Summarize benchmarks:\n{json.dumps(benchmarks, default=str)[:4000]}",
        fallback,
    )
    reports = list(state.get("reports", []))
    reports.append(report if isinstance(report, dict) else {"report": report})
    return {"status": "benchmark_reporting_complete", "reports": reports}


architecture_analysis_node = architecture_analysis
dependency_analysis_node = dependency_analysis
component_analysis_node = component_analysis
bottleneck_detection_node = bottleneck_detection
hypothesis_generation_node = hypothesis_generation
candidate_generation_node = candidate_generation
sandbox_benchmarking_node = sandbox_benchmarking
benchmark_reporting_node = benchmark_reporting
