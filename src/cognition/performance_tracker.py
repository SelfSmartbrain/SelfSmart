"""Performance tracker — records and queries agent-level performance metrics."""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)


class PerformanceTracker:
    """In-memory performance metrics store.

    Records timestamped metric observations and provides windowed
    aggregation queries for latency, success rate, token usage, and
    failure rate.  A production deployment should back this with a
    persistent time-series store; the in-memory implementation serves
    as a drop-in starting point.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        # metrics: name -> list of {value, timestamp, metadata}
        self._metrics: dict[str, list[dict[str, Any]]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def record_metric(
        self,
        metric_name: str,
        value: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a single metric observation.

        Args:
            metric_name: Dot-separated metric name (e.g. ``agent.latency``).
            value: Numeric metric value.
            metadata: Optional context (agent_type, session_id, …).
        """
        entry: dict[str, Any] = {
            "value": value,
            "timestamp": time.time(),
            "metadata": metadata or {},
        }
        self._metrics[metric_name].append(entry)
        logger.debug("metric_recorded", metric=metric_name, value=value)

    async def get_agent_latency(
        self,
        agent_type: str,
        window_hours: int = 24,
    ) -> float:
        """Return the average latency for *agent_type* over the given window.

        Latency metrics are expected to be recorded under the name
        ``agent.<agent_type>.latency``.
        """
        metric_name = f"agent.{agent_type}.latency"
        values = self._window_values(metric_name, window_hours)
        if not values:
            logger.info("no_latency_data", agent_type=agent_type)
            return 0.0
        avg = round(sum(values) / len(values), 4)
        logger.info("agent_latency", agent_type=agent_type, avg=avg, samples=len(values))
        return avg

    async def get_success_rate(
        self,
        agent_type: str,
        window_hours: int = 24,
    ) -> float:
        """Return the success rate for *agent_type* over the given window.

        Expects boolean-like values (1.0 = success, 0.0 = failure) under
        ``agent.<agent_type>.success``.
        """
        metric_name = f"agent.{agent_type}.success"
        values = self._window_values(metric_name, window_hours)
        if not values:
            logger.info("no_success_data", agent_type=agent_type)
            return 0.0
        rate = round(sum(values) / len(values), 4)
        logger.info("success_rate", agent_type=agent_type, rate=rate)
        return rate

    async def get_token_usage(
        self,
        window_hours: int = 24,
    ) -> dict[str, Any]:
        """Aggregate token usage across all agents for the window.

        Token metrics are recorded under ``tokens.input`` and
        ``tokens.output``.
        """
        input_values = self._window_values("tokens.input", window_hours)
        output_values = self._window_values("tokens.output", window_hours)
        usage: dict[str, Any] = {
            "total_input_tokens": int(sum(input_values)),
            "total_output_tokens": int(sum(output_values)),
            "total_tokens": int(sum(input_values) + sum(output_values)),
            "sample_count": len(input_values) + len(output_values),
        }
        logger.info("token_usage", **usage)
        return usage

    async def get_failure_rate(
        self,
        window_hours: int = 24,
    ) -> float:
        """Return the system-wide failure rate over the window.

        Uses all ``agent.*.success`` metrics inversely.
        """
        cutoff = time.time() - window_hours * 3600
        total = 0
        failures = 0
        for name, entries in self._metrics.items():
            if name.endswith(".success"):
                for e in entries:
                    if e["timestamp"] >= cutoff:
                        total += 1
                        if e["value"] < 0.5:
                            failures += 1
        if total == 0:
            return 0.0
        rate = round(failures / total, 4)
        logger.info("failure_rate", rate=rate, total=total)
        return rate

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _window_values(self, metric_name: str, window_hours: int) -> list[float]:
        """Return metric values within the time window."""
        cutoff = time.time() - window_hours * 3600
        return [
            e["value"]
            for e in self._metrics.get(metric_name, [])
            if e["timestamp"] >= cutoff
        ]
