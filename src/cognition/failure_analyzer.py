"""Failure analyzer — detects error patterns, clusters failures, and suggests fixes."""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)


class FailureAnalyzer:
    """Clusters, ranks, and generates fixes for recurring failures.

    Uses a combination of heuristic pattern matching and LLM-powered
    analysis to understand and remediate system errors.
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

    async def detect_patterns(self, errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Cluster similar errors into named patterns.

        Each returned dict contains:
          - pattern_name (str)
          - error_type (str)
          - count (int)
          - sample_errors (list)
          - severity (float 0-1)
        """
        logger.info("detecting_failure_patterns", error_count=len(errors))
        if not errors:
            return []

        try:
            groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for err in errors:
                key = err.get("type", err.get("error_type", "unknown"))
                groups[key].append(err)

            patterns: list[dict[str, Any]] = []
            for error_type, group in groups.items():
                severity = self._estimate_severity(group)
                patterns.append({
                    "pattern_name": f"{error_type}_cluster",
                    "error_type": error_type,
                    "count": len(group),
                    "sample_errors": group[:3],
                    "severity": severity,
                })

            logger.info("patterns_detected", pattern_count=len(patterns))
            return patterns
        except Exception as exc:
            logger.error("detect_patterns_failed", error=str(exc))
            return []

    async def cluster_failures(self, failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Group failures by their root-cause type.

        Returns clusters keyed by category with member failures.
        """
        logger.info("clustering_failures", failure_count=len(failures))
        if not failures:
            return []

        try:
            buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for failure in failures:
                category = self._categorize_failure(failure)
                buckets[category].append(failure)

            clusters = [
                {
                    "category": cat,
                    "count": len(members),
                    "failures": members,
                    "first_seen": members[0].get("timestamp"),
                    "last_seen": members[-1].get("timestamp"),
                }
                for cat, members in buckets.items()
            ]
            logger.info("failures_clustered", cluster_count=len(clusters))
            return clusters
        except Exception as exc:
            logger.error("cluster_failures_failed", error=str(exc))
            return []

    async def generate_fixes(self, pattern: dict[str, Any]) -> list[str]:
        """Use the LLM to suggest concrete fixes for an error pattern.

        Args:
            pattern: A pattern dict as produced by :meth:`detect_patterns`.

        Returns:
            A list of human-readable fix suggestions.
        """
        logger.info("generating_fixes", pattern=pattern.get("pattern_name"))
        system_prompt = (
            "You are an expert at diagnosing and fixing software failures in an "
            "autonomous research system. Given a failure pattern, suggest concrete, "
            "actionable fixes. Return a JSON array of strings. No markdown fences."
        )
        human_prompt = (
            f"Failure pattern:\n{json.dumps(pattern, indent=2, default=str)}\n\n"
            "Suggest fixes."
        )
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ])
            fixes: list[str] = json.loads(response.content)
            logger.info("fixes_generated", fix_count=len(fixes))
            return fixes
        except json.JSONDecodeError as exc:
            logger.error("fixes_json_parse_error", error=str(exc))
            return ["Review the error pattern manually and apply targeted fixes."]
        except Exception as exc:
            logger.error("generate_fixes_failed", error=str(exc))
            return []

    async def rank_failures(self, patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Sort failure patterns by *frequency × severity* (descending).

        Each pattern is annotated with a ``priority_score``.
        """
        logger.info("ranking_failures", pattern_count=len(patterns))
        try:
            for p in patterns:
                p["priority_score"] = round(
                    p.get("count", 1) * p.get("severity", 0.5), 4
                )
            ranked = sorted(patterns, key=lambda p: p["priority_score"], reverse=True)
            logger.info("failures_ranked", top_score=ranked[0]["priority_score"] if ranked else 0)
            return ranked
        except Exception as exc:
            logger.error("rank_failures_failed", error=str(exc))
            return patterns

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_severity(errors: list[dict[str, Any]]) -> float:
        """Heuristic severity estimate based on error metadata."""
        critical_keywords = {"fatal", "crash", "oom", "timeout", "deadlock"}
        severity = 0.3  # baseline
        for err in errors:
            msg = str(err.get("message", "")).lower()
            if any(kw in msg for kw in critical_keywords):
                severity = max(severity, 0.9)
                break
            if err.get("retries", 0) > 2:
                severity = max(severity, 0.7)
        return round(severity, 2)

    @staticmethod
    def _categorize_failure(failure: dict[str, Any]) -> str:
        """Map a failure to a coarse category."""
        error_type = str(failure.get("type", failure.get("error_type", ""))).lower()
        if "timeout" in error_type or "deadline" in error_type:
            return "timeout"
        if "auth" in error_type or "permission" in error_type:
            return "authentication"
        if "rate" in error_type or "throttl" in error_type:
            return "rate_limiting"
        if "parse" in error_type or "json" in error_type or "decode" in error_type:
            return "parsing"
        if "connect" in error_type or "network" in error_type:
            return "network"
        return "other"
