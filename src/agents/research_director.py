"""Research Director Agent."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from src.db.models import GeneratedGoal, ResearchTrack
from src.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ResearchDirector:
    """Manages multiple autonomous investigations, allocating tracks and monitoring progress."""

    def __init__(
        self,
        track_repo: BaseRepository[ResearchTrack],
    ) -> None:
        self.track_repo = track_repo

    async def evaluate_goal_for_track(self, goal: GeneratedGoal) -> ResearchTrack | None:
        """
        Evaluate an autonomously generated goal and, if it meets priority thresholds, 
        create a new Research Track for it.
        """
        logger.info(f"Director evaluating goal: {goal.title} (Curiosity: {goal.curiosity_score})")
        
        # Simple threshold heuristic
        if goal.curiosity_score < 0.4:
            logger.info("Goal rejected by Director: Curiosity score too low.")
            return None
            
        # Create a Research Track
        track = await self.track_repo.create(
            goal_id=goal.id,
            title=f"Track: {goal.title}",
            status="active",
            progress_percentage=0.0
        )
        
        logger.info(f"Created Research Track {track.id} for Goal {goal.id}")
        return track

    async def review_active_tracks(self) -> None:
        """
        Periodically review all active tracks, terminating low-value or stalled ones.
        """
        logger.info("Director is reviewing active research tracks...")
        # Placeholder for complex logic (e.g., checking timestamps, asking LLM to review progress)
        # In a real implementation, we would query self.track_repo for status='active'
        pass
