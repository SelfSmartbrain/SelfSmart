"""Learning velocity tracker — measures rates of knowledge, concept, and research growth."""
from __future__ import annotations

import time
from typing import Any

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)

_SECONDS_PER_DAY = 86_400


class LearningVelocityTracker:
    """Tracks how fast the system acquires knowledge.

    Computes growth rates for concepts, knowledge-graph nodes, and
    completed research tracks over configurable windows.  Also derives
    a *learning acceleration* value (second-order derivative of growth).
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        # Internal time-stamped event stores — in production these would
        # be backed by a database.
        self._concept_events: list[dict[str, Any]] = []
        self._knowledge_events: list[dict[str, Any]] = []
        self._research_events: list[dict[str, Any]] = []
        self._growth_history: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Event recording helpers (call these from other modules)
    # ------------------------------------------------------------------

    def record_concept(self, concept_id: str) -> None:
        """Register that a new concept has been learned."""
        self._concept_events.append({"id": concept_id, "timestamp": time.time()})

    def record_knowledge_node(self, node_id: str) -> None:
        """Register a new knowledge-graph node."""
        self._knowledge_events.append({"id": node_id, "timestamp": time.time()})

    def record_research_completion(self, track_id: str) -> None:
        """Register that a research track has been completed."""
        self._research_events.append({"id": track_id, "timestamp": time.time()})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def compute_concept_growth(self, window_days: int = 7) -> float:
        """Rate of new concepts acquired per day over the window.

        Returns:
            Average new concepts per day.
        """
        rate = self._daily_rate(self._concept_events, window_days)
        logger.info("concept_growth", rate=rate, window_days=window_days)
        return rate

    async def compute_knowledge_growth(self, window_days: int = 7) -> float:
        """Rate of new knowledge-graph nodes per day.

        Returns:
            Average new KG nodes per day.
        """
        rate = self._daily_rate(self._knowledge_events, window_days)
        logger.info("knowledge_growth", rate=rate, window_days=window_days)
        return rate

    async def compute_research_output(self, window_days: int = 7) -> float:
        """Rate of completed research tracks per day.

        Returns:
            Average completed tracks per day.
        """
        rate = self._daily_rate(self._research_events, window_days)
        logger.info("research_output", rate=rate, window_days=window_days)
        return rate

    async def compute_learning_acceleration(self) -> float:
        """Compute the delta of the overall growth rate.

        Compares the most recent growth snapshot to the previous one.
        A positive value indicates accelerating learning.

        Returns:
            Acceleration value (positive = speeding up).
        """
        try:
            current_rate = await self._current_growth_rate()
            self._growth_history.append({
                "rate": current_rate,
                "timestamp": time.time(),
            })

            if len(self._growth_history) < 2:
                logger.info("learning_acceleration", acceleration=0.0, note="insufficient history")
                return 0.0

            prev = self._growth_history[-2]["rate"]
            acceleration = round(current_rate - prev, 6)
            logger.info("learning_acceleration", acceleration=acceleration)
            return acceleration
        except Exception as exc:
            logger.error("compute_acceleration_failed", error=str(exc))
            return 0.0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _daily_rate(self, events: list[dict[str, Any]], window_days: int) -> float:
        """Count events within *window_days* and return a per-day rate."""
        cutoff = time.time() - window_days * _SECONDS_PER_DAY
        count = sum(1 for e in events if e["timestamp"] >= cutoff)
        return round(count / max(window_days, 1), 4)

    async def _current_growth_rate(self) -> float:
        """Aggregate growth rate across all event types (7-day window)."""
        concept = await self.compute_concept_growth(7)
        knowledge = await self.compute_knowledge_growth(7)
        research = await self.compute_research_output(7)
        return round(concept + knowledge + research, 4)
