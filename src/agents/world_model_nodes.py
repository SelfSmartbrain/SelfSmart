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
        logger.warning("World-model LLM call failed: %s", e)
    return fallback

class PatternDiscovery:
    async def discover_patterns(self, data: Any) -> List[Dict[str, Any]]:
        fallback = [{"id": "p1", "pattern": "no_patterns_detected", "confidence": 0.0}]
        if not data:
            return fallback
        patterns = await _llm_json(
            "You are a pattern recognition engine. Return only a JSON array of patterns.",
            f"Analyze this data for patterns:\n{json.dumps(data, default=str)[:4000]}",
            fallback,
        )
        return patterns if isinstance(patterns, list) else fallback

class CausalReasoning:
    async def infer_causality(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        fallback = []
        if not patterns:
            return fallback
        links = await _llm_json(
            "You infer causal relationships from patterns. Return only a JSON array.",
            f"Infer causal links from these patterns:\n{json.dumps(patterns, default=str)[:4000]}",
            fallback,
        )
        return links if isinstance(links, list) else fallback

class HypothesisGeneration:
    async def generate_hypotheses(self, causal_links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        fallback = [
            {
                "id": f"h{index}",
                "description": f"{link.get('cause', 'unknown')} influences {link.get('effect', 'unknown')}",
                "status": "proposed",
            }
            for index, link in enumerate(causal_links, start=1)
            if isinstance(link, dict)
        ]
        hypotheses = await _llm_json(
            "You generate testable hypotheses from causal links. Return only a JSON array.",
            f"Generate hypotheses from causal links:\n{json.dumps(causal_links, default=str)[:4000]}",
            fallback,
        )
        return hypotheses if isinstance(hypotheses, list) else fallback

class ExperimentDesign:
    async def design_experiment(self, hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        hypothesis_id = hypothesis.get("id", "unknown")
        fallback = {
            "id": f"exp_{hypothesis_id}",
            "hypothesis_id": hypothesis_id,
            "control": "baseline behavior",
            "treatment": "candidate intervention",
            "metric": "success_rate",
        }
        experiment = await _llm_json(
            "You design safe experiments for hypotheses. Return a JSON object.",
            f"Design an experiment for hypothesis:\n{json.dumps(hypothesis, default=str)[:3000]}",
            fallback,
        )
        return experiment if isinstance(experiment, dict) else fallback

class ExperimentExecution:
    async def run_experiment(self, experiment: Dict[str, Any]) -> Dict[str, Any]:
        fallback = {
            "experiment_id": experiment.get("id", "unknown"),
            "hypothesis_id": experiment.get("hypothesis_id", "unknown"),
            "result": "not_run",
            "p_value": 1.0,
            "notes": "No execution backend configured; recorded design only.",
        }
        result = await _llm_json(
            "You estimate experiment outcomes from available state. Return a JSON object.",
            f"Evaluate this experiment design conceptually:\n{json.dumps(experiment, default=str)[:3000]}",
            fallback,
        )
        return result if isinstance(result, dict) else fallback

class BeliefUpdate:
    async def update_beliefs(
        self,
        beliefs: List[Dict[str, Any]],
        result: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Update beliefs based on a single experiment result."""
        updated = list(beliefs)

        result_status = result.get("result", "unknown")
        hypothesis_id = result.get("hypothesis_id", "unknown")
        p_value = float(result.get("p_value", 1.0) or 1.0)

        new_belief = {
            "belief": f"hypothesis_{hypothesis_id}",
            "probability": max(0.0, 1.0 - p_value) if result_status == "confirmed" else p_value,
            "evidence": result_status,
            "experiment_id": result.get("experiment_id", "unknown"),
        }

        for index, belief in enumerate(updated):
            if belief.get("belief") == new_belief["belief"]:
                old_prob = float(belief.get("probability", 0.5) or 0.5)
                updated[index] = {
                    **belief,
                    "probability": (old_prob + new_belief["probability"]) / 2,
                    "evidence": result_status,
                    "experiment_id": new_belief["experiment_id"],
                }
                break
        else:
            updated.append(new_belief)

        return updated

class PredictionGeneration:
    async def generate_predictions(self, beliefs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        fallback = [
            {
                "id": f"pred_{index}",
                "prediction": f"{belief.get('belief', 'unknown')} remains likely",
                "confidence": belief.get("probability", 0.5),
            }
            for index, belief in enumerate(beliefs, start=1)
            if isinstance(belief, dict)
        ]
        predictions = await _llm_json(
            "You generate predictions from beliefs. Return only a JSON array.",
            f"Generate predictions from beliefs:\n{json.dumps(beliefs, default=str)[:4000]}",
            fallback,
        )
        return predictions if isinstance(predictions, list) else fallback

class WorldModelUpdate:
    async def update_model(self, beliefs: List[Dict[str, Any]], predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        fallback = {
            "status": "updated",
            "belief_count": len(beliefs),
            "prediction_count": len(predictions),
        }
        model_state = await _llm_json(
            "You update a world model summary. Return a JSON object.",
            "Update the world model from:\n"
            f"{json.dumps({'beliefs': beliefs, 'predictions': predictions}, default=str)[:4000]}",
            fallback,
        )
        return model_state if isinstance(model_state, dict) else fallback

async def pattern_discovery(state: Dict[str, Any]) -> Dict[str, Any]:
    """Discover patterns in data."""
    logger.info("Running pattern discovery...")
    discovery = PatternDiscovery()
    data = state.get("data", [])
    patterns = await discovery.discover_patterns(data)
    return {"patterns": patterns}

async def causal_reasoning(state: Dict[str, Any]) -> Dict[str, Any]:
    """Infer causal links from patterns."""
    logger.info("Running causal reasoning...")
    reasoning = CausalReasoning()
    patterns = state.get("patterns", [])
    causal_links = await reasoning.infer_causality(patterns)
    return {"causal_links": causal_links}

async def hypothesis_generation(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate hypotheses from causal links."""
    logger.info("Running hypothesis generation...")
    generator = HypothesisGeneration()
    causal_links = state.get("causal_links", [])
    hypotheses = await generator.generate_hypotheses(causal_links)
    return {"hypotheses": hypotheses}

async def experiment_design(state: Dict[str, Any]) -> Dict[str, Any]:
    """Design experiments for hypotheses."""
    logger.info("Running experiment design...")
    designer = ExperimentDesign()
    hypotheses = state.get("hypotheses", [])
    experiments = []
    for h in hypotheses:
        exp = await designer.design_experiment(h)
        experiments.append(exp)
    return {"experiments": experiments}

async def experiment_execution(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute experiments and get results."""
    logger.info("Running experiment execution...")
    executor = ExperimentExecution()
    experiments = state.get("experiments", [])
    results = []
    for exp in experiments:
        res = await executor.run_experiment(exp)
        results.append(res)
    return {"experiment_results": results}

async def belief_update(state: Dict[str, Any]) -> Dict[str, Any]:
    """Update beliefs based on experiment results."""
    logger.info("Running belief update...")
    updater = BeliefUpdate()
    beliefs = state.get("beliefs", [])
    results = state.get("experiment_results", [])
    for res in results:
        beliefs = await updater.update_beliefs(beliefs, res)
    return {"beliefs": beliefs}

async def prediction_generation(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate predictions based on current beliefs."""
    logger.info("Running prediction generation...")
    generator = PredictionGeneration()
    beliefs = state.get("beliefs", [])
    predictions = await generator.generate_predictions(beliefs)
    return {"predictions": predictions}

async def world_model_update(state: Dict[str, Any]) -> Dict[str, Any]:
    """Update the global world model."""
    logger.info("Running world model update...")
    updater = WorldModelUpdate()
    beliefs = state.get("beliefs", [])
    predictions = state.get("predictions", [])
    model_state = await updater.update_model(beliefs, predictions)
    return {"world_model_state": model_state}


pattern_discovery_node = pattern_discovery
causal_reasoning_node = causal_reasoning
hypothesis_generation_node = hypothesis_generation
experiment_design_node = experiment_design
experiment_execution_node = experiment_execution
belief_update_node = belief_update
prediction_generation_node = prediction_generation
world_model_update_node = world_model_update
