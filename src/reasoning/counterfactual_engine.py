'''
counterfactual_engine.py

Provides counterfactual reasoning capabilities for the ReasoningEngine.
Given a scenario description, it generates "what‑if" statements using a language model.
'''

import asyncio
import logging
from typing import Any
from src.agents.world_model_nodes import _llm_json

logger = logging.getLogger(__name__)

def _run_async(coro):
    """Run an async coroutine synchronously by creating a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

class CounterfactualEngine:
    def __init__(self, model_name: str = "gpt2"):
        # Note: model_name is kept for compatibility but not used since we use the LLM via _llm_json
        self.model_name = model_name

    def run(self, scenario: str) -> str:
        """Generate a counterfactual explanation using the LLM."""
        try:
            # We ask the LLM to return a JSON object with an "explanation" key.
            system = (
                "You are a helpful assistant that generates counterfactual explanations. "
                "Given a scenario, return a JSON object with a single key 'explanation' "
                "whose value is a string (1-2 sentences) explaining how the outcome might change "
                "if the scenario were different. Do not include any other text."
            )
            # We pass the scenario as a JSON string so the LLM can easily parse it.
            # The LLM is expected to output a JSON object.
            prompt = f'{{ "scenario": "{scenario}" }}'
            fallback = {"explanation": f"If {scenario} had been different, the outcome might change accordingly."}
            result = _run_async(_llm_json(system, prompt, fallback))
            if isinstance(result, dict) and "explanation" in result:
                explanation = result["explanation"]
                if isinstance(explanation, str):
                    return explanation
                else:
                    return str(explanation)
            else:
                # If the result is not as expected, use the fallback explanation.
                return f"If {scenario} had been different, the outcome might change accordingly."
        except Exception as e:
            logger.warning(f"Counterfactual generation failed: {e}")
            return f"If {scenario} had been different, the outcome might change accordingly."

    def __repr__(self) -> str:
        return f"CounterfactualEngine(model={self.model_name})"