from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
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
        logger.warning("Evolution node LLM call failed", error=str(e))
    return fallback


async def genome_generation(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node: Generates an initial cognitive genome."""
    logger.info("Executing genome_generation node")
    genome_data = state.get("genome_data", {})
    fallback = {
        "traits": genome_data.get("traits", []),
        "source_goal": state.get("goal"),
        "fitness": genome_data.get("fitness", 0.0),
    }
    genome = await _llm_json(
        "You generate a cognitive genome for an autonomous agent. Return a JSON object.",
        f"Generate or refine a genome from state:\n{json.dumps(state, default=str)[:4000]}",
        fallback,
    )
    return {"genome_generated": True, "genome": genome, "genome_data": genome}


async def mutation_generation(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node: Applies mutations to an existing genome."""
    logger.info("Executing mutation_generation node")
    genome = state.get("genome") or state.get("genome_data", {})
    fallback = [{"type": "parameter_tuning", "target": "fitness", "expected_delta": 0.0}]
    mutations = await _llm_json(
        "You propose safe genome mutations. Return only a JSON array.",
        f"Propose mutations for genome:\n{json.dumps(genome, default=str)[:4000]}",
        fallback,
    )
    return {"mutated": True, "mutations": mutations}


async def candidate_selection(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node: Selects the best candidates from a population."""
    logger.info("Executing candidate_selection node")
    candidates = state.get("candidates") or state.get("mutations", [])
    fallback = candidates[:3] if isinstance(candidates, list) else []
    selected = await _llm_json(
        "You select the best evolution candidates. Return only a JSON array.",
        f"Select candidates from:\n{json.dumps(candidates, default=str)[:4000]}",
        fallback,
    )
    return {"candidates_selected": True, "selected_candidates": selected}


async def evolution_cycle(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node: Manages a full evolution cycle."""
    logger.info("Executing evolution_cycle node")
    selected = state.get("selected_candidates", [])
    fallback = {
        "evaluated_candidates": len(selected) if isinstance(selected, list) else 0,
        "cycle_status": "completed",
    }
    cycle = await _llm_json(
        "You evaluate an evolution cycle. Return a JSON object.",
        f"Evaluate selected candidates:\n{json.dumps(selected, default=str)[:4000]}",
        fallback,
    )
    return {"cycle_completed": True, "evolution_cycle": cycle}


async def promotion_decision(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node: Decides if an architecture should be promoted."""
    logger.info("Executing promotion_decision node")
    cycle = state.get("evolution_cycle", {})
    fallback = {
        "promoted": bool(state.get("selected_candidates")),
        "reason": "Promote only when candidates are selected and no regressions are known.",
    }
    decision = await _llm_json(
        "You make conservative promotion decisions. Return a JSON object.",
        f"Decide promotion from evolution cycle:\n{json.dumps(cycle, default=str)[:4000]}",
        fallback,
    )
    promoted = (
        bool(decision.get("promoted", fallback["promoted"]))
        if isinstance(decision, dict)
        else False
    )
    return {"promoted": promoted, "promotion_decision": decision}


async def rollback_check(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node: Checks if a rollback is necessary based on fitness."""
    logger.info("Executing rollback_check node")
    regressions = state.get("regression_results", {})
    rollback_needed = (
        bool(regressions.get("regressions_found")) if isinstance(regressions, dict) else False
    )
    return {
        "rollback_needed": rollback_needed,
        "rollback_reason": "Regression detected" if rollback_needed else None,
    }


async def fitness_tracking(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node: Tracks the fitness of architectures/genomes."""
    logger.info("Executing fitness_tracking node")
    cycle = state.get("evolution_cycle", {})
    benchmark_results = state.get("benchmark_results", {})
    fitness_score = 0.0
    if isinstance(benchmark_results, dict):
        fitness_score = float(benchmark_results.get("score", 0.0) or 0.0)
    elif isinstance(cycle, dict):
        fitness_score = float(cycle.get("fitness", 0.0) or 0.0)
    history = list(state.get("fitness_history", []))
    history.append({"score": fitness_score, "promoted": state.get("promoted", False)})
    return {"fitness_tracked": True, "fitness_score": fitness_score, "fitness_history": history}


async def generation_tracking(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node: Tracks generational progress."""
    logger.info("Executing generation_tracking node")
    generation = int(state.get("generation", 0)) + 1
    return {
        "generation_tracked": True,
        "generation": generation,
        "generation_summary": {
            "fitness_score": state.get("fitness_score", 0.0),
            "rollback_needed": state.get("rollback_needed", False),
        },
    }


genome_generation_node = genome_generation
mutation_generation_node = mutation_generation
candidate_selection_node = candidate_selection
evolution_cycle_node = evolution_cycle
promotion_decision_node = promotion_decision
rollback_check_node = rollback_check
fitness_tracking_node = fitness_tracking
generation_tracking_node = generation_tracking
