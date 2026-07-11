"""Reflection agent — analyzes completed research tracks and produces structured reflections."""
from __future__ import annotations

import json
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)


class CognitionReflectionAgent:
    """Analyzes completed research tracks via LLM-powered reflection.

    Produces structured quality, confidence, and success scores along with
    actionable lessons learned and improvement suggestions.
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

    async def reflect_on_track(
        self,
        goal: str,
        track_results: dict[str, Any],
        errors: list[Any],
    ) -> dict[str, Any]:
        """Use the LLM to analyse a completed research track.

        Args:
            goal: The original research goal.
            track_results: Structured results produced by the track.
            errors: Any errors encountered during execution.

        Returns:
            A dict with keys: success_score, quality_score, confidence_score,
            lessons_learned, mistakes_found, improvement_suggestions,
            reflection_summary.
        """
        logger.info("reflecting_on_track", goal=goal, error_count=len(errors))

        system_prompt = (
            "You are an expert reflection analyst for an autonomous research system. "
            "Given a research goal, the results obtained, and any errors encountered, "
            "produce a JSON object with the following keys:\n"
            "  success_score (float 0-1): how well the goal was achieved\n"
            "  quality_score (float 0-1): quality of the results\n"
            "  confidence_score (float 0-1): confidence in the results\n"
            "  lessons_learned (list[str]): key takeaways\n"
            "  mistakes_found (list[str]): mistakes or missteps\n"
            "  improvement_suggestions (list[str]): actionable improvements\n"
            "  reflection_summary (str): short narrative summary\n"
            "Return ONLY valid JSON — no markdown fences."
        )

        human_prompt = (
            f"Goal: {goal}\n\n"
            f"Results:\n{json.dumps(track_results, indent=2, default=str)}\n\n"
            f"Errors:\n{json.dumps(errors, indent=2, default=str)}"
        )

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ])
            reflection = json.loads(response.content)
            logger.info(
                "reflection_complete",
                success_score=reflection.get("success_score"),
                quality_score=reflection.get("quality_score"),
            )
            return reflection
        except json.JSONDecodeError as exc:
            logger.error("reflection_json_parse_error", error=str(exc))
            return self._default_reflection(goal)
        except Exception as exc:
            logger.error("reflection_failed", error=str(exc))
            return self._default_reflection(goal)

    async def calculate_quality(self, results: dict[str, Any]) -> float:
        """Compute a heuristic quality metric for a set of results.

        The score is derived from completeness, depth, and internal
        consistency of the result data.
        """
        try:
            completeness = min(len(results) / 5.0, 1.0)
            depth = 0.0
            for value in results.values():
                if isinstance(value, dict):
                    depth += 0.2
                elif isinstance(value, list) and len(value) > 0:
                    depth += 0.15
                elif value:
                    depth += 0.1
            depth = min(depth, 1.0)

            quality = round((completeness * 0.4 + depth * 0.6), 4)
            logger.info("quality_calculated", quality=quality)
            return quality
        except Exception as exc:
            logger.error("quality_calculation_failed", error=str(exc))
            return 0.0

    async def save_reflection(self, reflection: dict[str, Any], session: Any) -> None:
        """Persist a reflection dict to the database via the provided session.

        Args:
            reflection: The reflection payload to save.
            session: An async DB session (e.g. SQLAlchemy AsyncSession).
        """
        try:
            from src.db.models import Reflection  # deferred to avoid circular imports

            record = Reflection(**reflection)
            session.add(record)
            await session.commit()
            logger.info("reflection_saved")
        except ImportError:
            logger.warning("reflection_model_not_available — skipping persistence")
        except Exception as exc:
            logger.error("reflection_save_failed", error=str(exc))
            await session.rollback()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _default_reflection(goal: str) -> dict[str, Any]:
        """Return a safe default reflection when the LLM call fails."""
        return {
            "success_score": 0.0,
            "quality_score": 0.0,
            "confidence_score": 0.0,
            "lessons_learned": [],
            "mistakes_found": ["Reflection generation failed"],
            "improvement_suggestions": ["Retry reflection with more context"],
            "reflection_summary": f"Reflection could not be generated for goal: {goal}",
        }
