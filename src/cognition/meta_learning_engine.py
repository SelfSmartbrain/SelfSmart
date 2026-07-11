"""Meta-learning engine — discovers patterns across reflections, strategies, and failures."""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)


class MetaLearningEngine:
    """Learns from historical reflections, strategies, and failure data.

    Discovers recurring patterns, re-ranks strategies by observed success,
    and recommends system-level improvements.
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

    async def learn_from_history(
        self,
        reflections: list[Any],
        strategies: list[Any],
        failures: list[Any],
    ) -> dict[str, Any]:
        """Synthesise meta-insights from historical data.

        Combines reflections, strategies, and failures into a unified
        meta-learning report including discovered patterns, strategy
        rankings, and improvement recommendations.
        """
        logger.info(
            "learning_from_history",
            reflections=len(reflections),
            strategies=len(strategies),
            failures=len(failures),
        )
        try:
            patterns = await self.discover_patterns(
                [{"source": "reflection", "data": r} for r in reflections]
                + [{"source": "failure", "data": f} for f in failures]
            )
            ranked = await self.update_rankings(
                [s if isinstance(s, dict) else {"strategy": s} for s in strategies]
            )
            improvements = await self.recommend_improvements({
                "pattern_count": len(patterns),
                "strategy_count": len(ranked),
                "failure_count": len(failures),
                "reflection_count": len(reflections),
            })

            report: dict[str, Any] = {
                "patterns": patterns,
                "ranked_strategies": ranked,
                "improvements": improvements,
                "meta_summary": (
                    f"Analyzed {len(reflections)} reflections, "
                    f"{len(strategies)} strategies, {len(failures)} failures. "
                    f"Found {len(patterns)} patterns."
                ),
            }
            logger.info("meta_learning_complete", pattern_count=len(patterns))
            return report
        except Exception as exc:
            logger.error("learn_from_history_failed", error=str(exc))
            return {"patterns": [], "ranked_strategies": [], "improvements": [], "meta_summary": "Meta-learning failed."}

    async def discover_patterns(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Find recurring patterns across mixed source data.

        Groups entries by source, then looks for common themes.
        """
        logger.info("discovering_patterns", data_count=len(data))
        if not data:
            return []

        try:
            groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for item in data:
                groups[item.get("source", "unknown")].append(item)

            patterns: list[dict[str, Any]] = []
            for source, items in groups.items():
                if len(items) >= 2:
                    patterns.append({
                        "source": source,
                        "frequency": len(items),
                        "type": "recurring",
                        "description": f"Recurring {source} pattern ({len(items)} occurrences)",
                        "samples": items[:3],
                    })
            logger.info("patterns_discovered", count=len(patterns))
            return patterns
        except Exception as exc:
            logger.error("discover_patterns_failed", error=str(exc))
            return []

    async def update_rankings(self, strategies: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Re-rank strategies by observed success rate.

        Each strategy dict should include an optional ``success_rate`` field.
        Strategies are sorted descending by that value; ties broken by
        ``usage_count``.
        """
        logger.info("updating_rankings", strategy_count=len(strategies))
        try:
            for s in strategies:
                s.setdefault("success_rate", 0.5)
                s.setdefault("usage_count", 0)
                s["rank_score"] = round(
                    s["success_rate"] * 0.7 + min(s["usage_count"] / 100.0, 1.0) * 0.3,
                    4,
                )

            ranked = sorted(strategies, key=lambda s: s["rank_score"], reverse=True)
            for idx, s in enumerate(ranked, 1):
                s["rank"] = idx
            logger.info("rankings_updated")
            return ranked
        except Exception as exc:
            logger.error("update_rankings_failed", error=str(exc))
            return strategies

    async def recommend_improvements(self, metrics: dict[str, Any]) -> list[str]:
        """Generate system-level improvement suggestions via the LLM.

        Args:
            metrics: Aggregated system metrics.

        Returns:
            A list of improvement suggestion strings.
        """
        logger.info("recommending_improvements", metrics=metrics)
        system_prompt = (
            "You are a meta-learning advisor for an autonomous research platform. "
            "Given aggregate metrics, suggest concrete improvements the system should "
            "adopt. Return a JSON array of strings. No markdown fences."
        )
        human_prompt = f"System metrics:\n{json.dumps(metrics, indent=2, default=str)}"

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ])
            suggestions: list[str] = json.loads(response.content)
            logger.info("improvements_recommended", count=len(suggestions))
            return suggestions
        except json.JSONDecodeError as exc:
            logger.error("improvements_json_parse_error", error=str(exc))
            return ["Review system metrics and identify bottlenecks manually."]
        except Exception as exc:
            logger.error("recommend_improvements_failed", error=str(exc))
            return []
