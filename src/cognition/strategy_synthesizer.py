"""Strategy synthesizer — generates, scores, and optimises research strategies via LLM."""
from __future__ import annotations

import json
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)


class StrategySynthesizer:
    """Creates, evaluates, and iteratively refines research strategies.

    Uses LLM-powered reasoning combined with historical performance data
    to produce high-quality strategies tailored to a given goal and domain.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.llm = ChatAnthropic(
            model=self.settings.anthropic_model,
            api_key=self.settings.ANTHROPIC_API_KEY,
            max_tokens=4096,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_strategy(
        self,
        goal: str,
        domain: str,
        history: list[Any],
    ) -> dict[str, Any]:
        """Use the LLM to create a research strategy.

        Args:
            goal: The research objective.
            domain: Knowledge domain (e.g. "machine learning").
            history: Previous strategy results for context.

        Returns:
            A dict describing the strategy with keys such as
            ``name``, ``steps``, ``expected_outcome``, ``risk_factors``,
            ``estimated_quality``.
        """
        logger.info("generating_strategy", goal=goal, domain=domain)

        system_prompt = (
            "You are a research strategist for an autonomous AGI platform. "
            "Given a goal, domain, and historical strategy performance, "
            "design a new research strategy. Return a JSON object with:\n"
            "  name (str): short strategy name\n"
            "  steps (list[str]): ordered action steps\n"
            "  expected_outcome (str): what success looks like\n"
            "  risk_factors (list[str]): potential risks\n"
            "  estimated_quality (float 0-1): expected quality\n"
            "Return ONLY valid JSON — no markdown fences."
        )

        history_summary = json.dumps(history[:10], indent=2, default=str) if history else "No history."
        human_prompt = (
            f"Goal: {goal}\nDomain: {domain}\n\n"
            f"Previous strategy history:\n{history_summary}"
        )

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ])
            strategy: dict[str, Any] = json.loads(response.content)
            logger.info("strategy_generated", name=strategy.get("name"))
            return strategy
        except json.JSONDecodeError as exc:
            logger.error("strategy_json_parse_error", error=str(exc))
            return self._default_strategy(goal, domain)
        except Exception as exc:
            logger.error("generate_strategy_failed", error=str(exc))
            return self._default_strategy(goal, domain)

    async def score_strategy(
        self,
        strategy: dict[str, Any],
        past_results: list[Any],
    ) -> float:
        """Compute the expected effectiveness score for a strategy.

        Scoring considers strategy completeness and historical
        similarity to previously successful approaches.

        Args:
            strategy: The strategy to evaluate.
            past_results: Prior execution results for comparison.

        Returns:
            A float between 0 and 1.
        """
        logger.info("scoring_strategy", name=strategy.get("name"))
        try:
            # Completeness factor
            steps = strategy.get("steps", [])
            completeness = min(len(steps) / 5.0, 1.0)

            # Risk discount
            risks = strategy.get("risk_factors", [])
            risk_penalty = min(len(risks) * 0.05, 0.3)

            # Historical bonus — if past results exist and show high quality
            history_bonus = 0.0
            if past_results:
                avg_quality = sum(
                    r.get("quality_score", r.get("estimated_quality", 0.5))
                    for r in past_results
                    if isinstance(r, dict)
                ) / len(past_results)
                history_bonus = avg_quality * 0.2

            score = round(
                max(0.0, min(1.0, completeness * 0.5 + history_bonus + 0.3 - risk_penalty)),
                4,
            )
            logger.info("strategy_scored", score=score)
            return score
        except Exception as exc:
            logger.error("score_strategy_failed", error=str(exc))
            return 0.5

    async def optimize_strategy(
        self,
        strategy: dict[str, Any],
        feedback: list[Any],
    ) -> dict[str, Any]:
        """Refine an existing strategy using execution feedback.

        Args:
            strategy: The original strategy to refine.
            feedback: Feedback items (e.g. reflection dicts, error logs).

        Returns:
            An updated strategy dict.
        """
        logger.info("optimizing_strategy", name=strategy.get("name"))

        system_prompt = (
            "You are a strategy optimiser. Given an existing strategy and user/system "
            "feedback, produce an improved version. Return a JSON object with the same "
            "schema as the original strategy (name, steps, expected_outcome, "
            "risk_factors, estimated_quality). No markdown fences."
        )
        human_prompt = (
            f"Current strategy:\n{json.dumps(strategy, indent=2, default=str)}\n\n"
            f"Feedback:\n{json.dumps(feedback[:10], indent=2, default=str)}"
        )

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ])
            optimized: dict[str, Any] = json.loads(response.content)
            logger.info("strategy_optimized", name=optimized.get("name"))
            return optimized
        except json.JSONDecodeError as exc:
            logger.error("optimize_json_parse_error", error=str(exc))
            return strategy  # return original on failure
        except Exception as exc:
            logger.error("optimize_strategy_failed", error=str(exc))
            return strategy

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _default_strategy(goal: str, domain: str) -> dict[str, Any]:
        return {
            "name": f"default_{domain}_strategy",
            "steps": [
                "Define scope and constraints",
                "Gather background information",
                "Identify key knowledge gaps",
                "Execute targeted research",
                "Synthesize findings",
            ],
            "expected_outcome": f"Comprehensive understanding of: {goal}",
            "risk_factors": ["Insufficient data", "Domain complexity"],
            "estimated_quality": 0.5,
        }
