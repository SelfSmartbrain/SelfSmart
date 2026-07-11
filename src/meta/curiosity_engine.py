"""Curiosity Engine."""

from __future__ import annotations

import logging
from typing import Any

from src.db.models import CuriosityScore
from src.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class CuriosityEngine:
    """Evaluates targets and generates curiosity scores to drive autonomous goal generation."""

    def __init__(self, repo: BaseRepository[CuriosityScore]) -> None:
        self.repo = repo

    def calculate_score(self, novelty: float, uncertainty: float, impact: float, importance: float) -> float:
        """
        Calculate overall curiosity score.
        Formula: curiosity_score = novelty + uncertainty + impact + importance
        Normalized to 0.0 - 1.0 (assuming inputs are 0.0 - 1.0 each and we average them or sum/4)
        """
        raw_score = novelty + uncertainty + impact + importance
        return raw_score / 4.0

    async def evaluate_gap(self, gap: dict[str, Any]) -> float:
        """
        Evaluate a Knowledge Gap and return a curiosity score.
        Higher importance and lower confidence (higher uncertainty) = higher curiosity.
        """
        importance = gap.get("importance", 0.5)
        confidence = gap.get("confidence", 0.5)
        uncertainty = 1.0 - confidence
        
        # Heuristics for novelty and impact
        novelty = 0.8  # Assume new gaps are fairly novel
        impact = importance * 1.2  # High importance implies high impact
        
        impact = min(1.0, impact) # Cap at 1.0
        
        score = self.calculate_score(novelty, uncertainty, impact, importance)
        
        logger.debug(f"Evaluated gap for domain {gap.get('domain')} -> Curiosity: {score:.2f}")
        return score

    async def persist_score(self, target_id: str, target_type: str, novelty: float, uncertainty: float, impact: float, importance: float) -> CuriosityScore:
        """Save the calculated score to the database."""
        total_score = self.calculate_score(novelty, uncertainty, impact, importance)
        
        score_record = await self.repo.create(
            target_id=target_id,
            target_type=target_type,
            novelty=novelty,
            uncertainty=uncertainty,
            impact=impact,
            importance=importance,
            total_score=total_score
        )
        return score_record
