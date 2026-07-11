"""Self-improvement engine — evaluates system health and generates concrete improvements."""
from __future__ import annotations

import json
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)


class SelfImprovementEngine:
    """Performs holistic system evaluation and produces ranked improvement plans.

    Examines metrics, strategies, and skills to identify weaknesses and
    generate actionable upgrades for agents and workflows.
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

    async def evaluate_system(
        self,
        metrics: dict[str, Any],
        strategies: list[Any],
        skills: list[Any],
    ) -> dict[str, Any]:
        """Run a full system evaluation.

        Combines quantitative metrics with qualitative assessment of
        strategies and skills to produce a structured evaluation report.

        Args:
            metrics: Current system performance metrics.
            strategies: Active strategy descriptors.
            skills: Registered skill descriptors.

        Returns:
            Evaluation dict with ``overall_score``, ``strengths``,
            ``weaknesses``, ``bottlenecks``, and ``recommendations``.
        """
        logger.info(
            "evaluating_system",
            metric_keys=list(metrics.keys()),
            strategy_count=len(strategies),
            skill_count=len(skills),
        )
        try:
            system_prompt = (
                "You are a systems evaluator for an autonomous AGI platform. "
                "Given system metrics, active strategies, and registered skills, "
                "produce a JSON evaluation with:\n"
                "  overall_score (float 0-1)\n"
                "  strengths (list[str])\n"
                "  weaknesses (list[str])\n"
                "  bottlenecks (list[str])\n"
                "  recommendations (list[str])\n"
                "Return ONLY valid JSON — no markdown fences."
            )
            human_prompt = (
                f"Metrics:\n{json.dumps(metrics, indent=2, default=str)}\n\n"
                f"Strategies ({len(strategies)}):\n"
                f"{json.dumps(strategies[:10], indent=2, default=str)}\n\n"
                f"Skills ({len(skills)}):\n"
                f"{json.dumps(skills[:10], indent=2, default=str)}"
            )

            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ])
            evaluation: dict[str, Any] = json.loads(response.content)
            logger.info("system_evaluated", overall_score=evaluation.get("overall_score"))
            return evaluation
        except json.JSONDecodeError as exc:
            logger.error("evaluation_json_parse_error", error=str(exc))
            return self._default_evaluation()
        except Exception as exc:
            logger.error("evaluate_system_failed", error=str(exc))
            return self._default_evaluation()

    async def generate_improvements(
        self,
        evaluation: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate concrete improvement actions from an evaluation.

        Each improvement contains ``area``, ``action``, ``priority``,
        and ``expected_impact``.
        """
        logger.info("generating_improvements")
        try:
            improvements: list[dict[str, Any]] = []

            for weakness in evaluation.get("weaknesses", []):
                improvements.append({
                    "area": "weakness",
                    "action": f"Address: {weakness}",
                    "priority": "high",
                    "expected_impact": 0.7,
                })

            for bottleneck in evaluation.get("bottlenecks", []):
                improvements.append({
                    "area": "bottleneck",
                    "action": f"Resolve: {bottleneck}",
                    "priority": "critical",
                    "expected_impact": 0.8,
                })

            for rec in evaluation.get("recommendations", []):
                improvements.append({
                    "area": "recommendation",
                    "action": rec,
                    "priority": "medium",
                    "expected_impact": 0.5,
                })

            # Sort by expected impact descending
            improvements.sort(key=lambda i: i["expected_impact"], reverse=True)
            logger.info("improvements_generated", count=len(improvements))
            return improvements
        except Exception as exc:
            logger.error("generate_improvements_failed", error=str(exc))
            return []

    async def rank_agents(
        self,
        agent_metrics: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Rank agents by composite effectiveness score.

        ``agent_metrics`` maps agent names/types to their metric dicts.
        Each agent metric should include ``success_rate``, ``avg_latency``,
        and ``task_count``.
        """
        logger.info("ranking_agents", agent_count=len(agent_metrics))
        try:
            ranked: list[dict[str, Any]] = []
            for agent_name, m in agent_metrics.items():
                if not isinstance(m, dict):
                    continue
                success = m.get("success_rate", 0.5)
                latency = m.get("avg_latency", 1.0)
                tasks = m.get("task_count", 0)

                # Composite: success weighted highest, latency penalised, volume bonus
                effectiveness = round(
                    success * 0.6
                    + max(0.0, 1.0 - latency / 60.0) * 0.2
                    + min(tasks / 100.0, 1.0) * 0.2,
                    4,
                )
                ranked.append({
                    "agent": agent_name,
                    "effectiveness": effectiveness,
                    "success_rate": success,
                    "avg_latency": latency,
                    "task_count": tasks,
                })

            ranked.sort(key=lambda a: a["effectiveness"], reverse=True)
            for idx, entry in enumerate(ranked, 1):
                entry["rank"] = idx

            logger.info("agents_ranked", top_agent=ranked[0]["agent"] if ranked else None)
            return ranked
        except Exception as exc:
            logger.error("rank_agents_failed", error=str(exc))
            return []

    async def optimize_workflows(
        self,
        current_flow: dict[str, Any],
    ) -> dict[str, Any]:
        """Suggest workflow optimisations via the LLM.

        Args:
            current_flow: A description of the current workflow (steps, agents, etc.).

        Returns:
            An optimised workflow dict.
        """
        logger.info("optimizing_workflows")
        system_prompt = (
            "You are a workflow optimisation expert for an AGI platform. "
            "Given a current workflow description, suggest an improved version "
            "that reduces latency, increases reliability, and maximises quality. "
            "Return a JSON object with keys: steps (list[str]), "
            "parallelizable (list[str]), estimated_speedup (float), "
            "changes_made (list[str]). No markdown fences."
        )
        human_prompt = f"Current workflow:\n{json.dumps(current_flow, indent=2, default=str)}"

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ])
            optimized: dict[str, Any] = json.loads(response.content)
            logger.info("workflows_optimized", speedup=optimized.get("estimated_speedup"))
            return optimized
        except json.JSONDecodeError as exc:
            logger.error("optimize_json_parse_error", error=str(exc))
            return current_flow
        except Exception as exc:
            logger.error("optimize_workflows_failed", error=str(exc))
            return current_flow

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _default_evaluation() -> dict[str, Any]:
        return {
            "overall_score": 0.0,
            "strengths": [],
            "weaknesses": ["Evaluation could not be completed"],
            "bottlenecks": [],
            "recommendations": ["Retry evaluation with updated metrics"],
        }
