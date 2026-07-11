"""Skill discovery — identifies, extracts, and registers reusable agent skills from execution logs."""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

import uuid6
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)


class SkillDiscovery:
    """Mines execution logs to discover repeatable agent workflows.

    Discovered workflows are registered as *skills* that the system can
    reuse in future research tracks.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.llm = ChatAnthropic(
            model=self.settings.anthropic_model,
            api_key=self.settings.ANTHROPIC_API_KEY,
            max_tokens=4096,
        )
        self._skill_registry: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def discover_skills(
        self,
        execution_logs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Find repeatable workflows in execution logs.

        Args:
            execution_logs: A list of structured log entries from agent runs.

        Returns:
            A list of skill descriptors with ``name``, ``pattern``,
            ``frequency``, and ``confidence``.
        """
        logger.info("discovering_skills", log_count=len(execution_logs))
        if not execution_logs:
            return []

        try:
            patterns = await self.extract_patterns(execution_logs)
            skills: list[dict[str, Any]] = []
            for pattern in patterns:
                if pattern.get("frequency", 0) >= 2:
                    skills.append({
                        "name": pattern.get("name", "unnamed_skill"),
                        "pattern": pattern,
                        "frequency": pattern["frequency"],
                        "confidence": min(pattern["frequency"] / 10.0, 1.0),
                    })
            logger.info("skills_discovered", count=len(skills))
            return skills
        except Exception as exc:
            logger.error("discover_skills_failed", error=str(exc))
            return []

    async def extract_patterns(
        self,
        logs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Identify common action sequences in execution logs.

        Groups log entries by action type and finds frequently recurring
        sub-sequences.
        """
        logger.info("extracting_patterns", log_count=len(logs))
        if not logs:
            return []

        try:
            action_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for entry in logs:
                action = entry.get("action", entry.get("step", "unknown"))
                action_groups[str(action)].append(entry)

            patterns: list[dict[str, Any]] = []
            for action, entries in action_groups.items():
                if len(entries) >= 2:
                    patterns.append({
                        "name": f"skill_{action}",
                        "action": action,
                        "frequency": len(entries),
                        "sample_entries": entries[:3],
                    })

            patterns.sort(key=lambda p: p["frequency"], reverse=True)
            logger.info("patterns_extracted", count=len(patterns))
            return patterns
        except Exception as exc:
            logger.error("extract_patterns_failed", error=str(exc))
            return []

    async def register_skill(self, skill_data: dict[str, Any]) -> dict[str, Any]:
        """Create and register a new skill entry.

        Args:
            skill_data: Skill descriptor including at minimum ``name`` and ``pattern``.

        Returns:
            The registered skill with an assigned ``skill_id``.
        """
        logger.info("registering_skill", name=skill_data.get("name"))
        try:
            skill_id = str(uuid6.uuid7())
            skill = {
                "skill_id": skill_id,
                "name": skill_data.get("name", "unnamed_skill"),
                "pattern": skill_data.get("pattern"),
                "frequency": skill_data.get("frequency", 0),
                "confidence": skill_data.get("confidence", 0.0),
                "success_rate": 0.0,
                "execution_count": 0,
            }
            self._skill_registry[skill_id] = skill
            logger.info("skill_registered", skill_id=skill_id)
            return skill
        except Exception as exc:
            logger.error("register_skill_failed", error=str(exc))
            return {"skill_id": None, "error": str(exc)}

    async def evaluate_skill(
        self,
        skill_id: str,
        executions: list[Any],
    ) -> float:
        """Calculate the success rate of a registered skill.

        Args:
            skill_id: The unique skill identifier.
            executions: Execution result dicts; each should have a
                ``success`` boolean key.

        Returns:
            Success rate as a float between 0 and 1.
        """
        logger.info("evaluating_skill", skill_id=skill_id, execution_count=len(executions))
        try:
            if not executions:
                return 0.0

            successes = sum(
                1 for e in executions
                if (isinstance(e, dict) and e.get("success", False))
            )
            rate = round(successes / len(executions), 4)

            # Update registry if skill exists
            if skill_id in self._skill_registry:
                self._skill_registry[skill_id]["success_rate"] = rate
                self._skill_registry[skill_id]["execution_count"] = len(executions)

            logger.info("skill_evaluated", skill_id=skill_id, success_rate=rate)
            return rate
        except Exception as exc:
            logger.error("evaluate_skill_failed", error=str(exc))
            return 0.0
