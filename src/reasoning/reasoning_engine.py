'''reasoning_engine.py
 
Core System‑2 reasoning component. Provides multi‑step planning, multi‑step planning, hypothesis generation, and counterfactual simulation.
Uses a simple tree search over generated hypotheses.
''' 

import logging
from typing import List, Any
from .search_engine import SearchEngine
from .hypothesis_tree import HypothesisTree
from .counterfactual_engine import CounterfactualEngine
from src.agents.world_model_nodes import _llm_json

logger = logging.getLogger(__name__)

class ReasoningEngine:
    def __init__(self, search_engine: SearchEngine, counterfactual_engine: CounterfactualEngine):
        self.search = search_engine
        self._counterfactual = counterfactual_engine

    def plan(self, goal: str, context: List[Any]) -> List[str]:
        """Generate a sequential plan to achieve `goal`.
        
        This method:
        1. Retrieve relevant memories via search.
        2. Generate hypotheses (steps) via LLM.
        3. Evaluate via hypothesis tree.
        """
        relevant = self.search.retrieve(goal, top_k=5)
        # LLM-backed hypothesis generation
        try:
            # Prepare context string (simple concatenation)
            context_str = "\n".join([str(c) for c in context])
            system = (
                "You are a helpful assistant that generates step-by-step plans to achieve a goal. "
                "Given a goal and some context, produce a JSON object with a key 'hypotheses' whose value is a list of strings, "
                "each string being a step in the plan. Return ONLY the JSON object."
            )
            prompt = f"Goal: {goal}\nContext:\n{context_str}"
            fallback = {"hypotheses": [f"Step {i+1}: {goal} subtask" for i in range(3)]}
            result: Any = _llm_json(system, prompt, fallback)
            if isinstance(result, dict) and "hypotheses" in result:
                hypotheses = result["hypotheses"]
                # Ensure we have a list of strings
                if not isinstance(hypotheses, list):
                    hypotheses = [str(hypotheses)]
                hypotheses = [str(h) for h in hypotheses]
            else:
                hypotheses = [f"Step {i+1}: {goal} subtask" for i in range(3)]
        except Exception as e:
            logger.warning("LLM hypothesis generation failed: %s", e)
            hypotheses = [f"Step {i+1}: {goal} subtask" for i in range(3)]
        
        tree = HypothesisTree(hypotheses)
        best_path = tree.select_best()
        return best_path

    def counterfactual(self, scenario: str) -> str:
        """Run a counterfactual simulation for a given scenario using the CounterfactualEngine."""
        return self._counterfactual.run(scenario)

    def __repr__(self) -> str:
        return "ReasoningEngine()"