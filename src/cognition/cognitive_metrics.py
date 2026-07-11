"""Cognitive metrics calculator — computes a full suite of system intelligence metrics."""
from __future__ import annotations

from typing import Any

from src.config.logging import get_logger
from src.config.settings import get_settings
from src.cognition.learning_velocity import LearningVelocityTracker
from src.cognition.performance_tracker import PerformanceTracker

logger = get_logger(__name__)


class CognitiveMetricsCalculator:
    """Aggregates all cognition-level metrics into a single report.

    Computes knowledge_growth_rate, learning_velocity, autonomy_score,
    research_efficiency, goal_completion_rate, curiosity_efficiency,
    strategy_effectiveness, and skill_utilization.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.velocity_tracker = LearningVelocityTracker()
        self.performance_tracker = PerformanceTracker()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def calculate_all(self) -> dict[str, Any]:
        """Return a dict containing all cognitive metrics.

        Keys:
            knowledge_growth_rate, learning_velocity, autonomy_score,
            research_efficiency, goal_completion_rate, curiosity_efficiency,
            strategy_effectiveness, skill_utilization.
        """
        logger.info("calculating_all_cognitive_metrics")
        try:
            knowledge_growth = await self.velocity_tracker.compute_knowledge_growth()
            concept_growth = await self.velocity_tracker.compute_concept_growth()
            research_output = await self.velocity_tracker.compute_research_output()
            acceleration = await self.velocity_tracker.compute_learning_acceleration()

            # Learning velocity: composite of concept + knowledge growth
            learning_velocity = round(concept_growth + knowledge_growth, 4)

            # Autonomy: ratio of automated tasks to total — approximated
            # via success rate across all agent types
            failure_rate = await self.performance_tracker.get_failure_rate()
            autonomy_score = round(1.0 - failure_rate, 4)

            # Research efficiency: output per unit cost (tokens)
            token_usage = await self.performance_tracker.get_token_usage()
            total_tokens = token_usage.get("total_tokens", 1) or 1
            research_efficiency = round(research_output / (total_tokens / 1_000_000 + 1), 4)

            # Goal completion: proxy via system-wide success rate
            goal_completion_rate = round(1.0 - failure_rate, 4)

            # Curiosity efficiency: concepts discovered per research track
            curiosity_efficiency = round(
                concept_growth / (research_output + 0.01), 4
            )

            # Strategy effectiveness: average concept growth weighted by
            # research output
            strategy_effectiveness = round(
                (concept_growth * 0.4 + research_output * 0.6), 4
            )

            # Skill utilization: placeholder — requires integration with
            # SkillDiscovery registry
            skill_utilization = 0.0

            metrics: dict[str, Any] = {
                "knowledge_growth_rate": knowledge_growth,
                "learning_velocity": learning_velocity,
                "autonomy_score": autonomy_score,
                "research_efficiency": research_efficiency,
                "goal_completion_rate": goal_completion_rate,
                "curiosity_efficiency": curiosity_efficiency,
                "strategy_effectiveness": strategy_effectiveness,
                "skill_utilization": skill_utilization,
                "learning_acceleration": acceleration,
            }
            logger.info("cognitive_metrics_calculated", **metrics)
            return metrics
        except Exception as exc:
            logger.error("calculate_all_failed", error=str(exc))
            return {
                "knowledge_growth_rate": 0.0,
                "learning_velocity": 0.0,
                "autonomy_score": 0.0,
                "research_efficiency": 0.0,
                "goal_completion_rate": 0.0,
                "curiosity_efficiency": 0.0,
                "strategy_effectiveness": 0.0,
                "skill_utilization": 0.0,
            }
