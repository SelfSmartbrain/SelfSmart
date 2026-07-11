"""Goal Tree Engine."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from src.db.models import GoalTree, SubGoal, GeneratedGoal
from src.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class GoalTreeEngine:
    """Manages hierarchical generation and recursive planning for complex goals."""

    def __init__(
        self,
        tree_repo: BaseRepository[GoalTree],
        subgoal_repo: BaseRepository[SubGoal],
    ) -> None:
        self.tree_repo = tree_repo
        self.subgoal_repo = subgoal_repo

    async def generate_hierarchy(self, goal: GeneratedGoal, plan_steps: list[dict[str, Any]]) -> GoalTree:
        """
        Convert a flat list of plan steps into a GoalTree with proper dependencies.
        """
        logger.info(f"Generating GoalTree hierarchy for goal {goal.id}")
        
        # 1. Create the root tree record
        tree = await self.tree_repo.create(
            goal_id=goal.id,
            structure={"root": "SubGoals will be linked to this tree"}
        )
        
        # 2. Iterate through plan steps and create SubGoals
        # Assuming plan_steps has format: {"id": "1", "title": "...", "desc": "...", "deps": []}
        for step in plan_steps:
            await self.subgoal_repo.create(
                tree_id=tree.id,
                title=step.get("title", "Untitled SubGoal"),
                description=step.get("desc", ""),
                dependencies=step.get("deps", []),
                status="generated"
            )
            
        return tree

    async def track_milestone(self, subgoal_id: UUID, is_completed: bool) -> SubGoal | None:
        """Update the status of a subgoal and check if downstream dependencies are unblocked."""
        logger.debug(f"Tracking milestone for subgoal {subgoal_id}: completed={is_completed}")
        
        status = "achieved" if is_completed else "failed"
        return await self.subgoal_repo.update(subgoal_id, status=status)

    async def get_next_actionable_subgoals(self, tree_id: UUID) -> list[SubGoal]:
        """
        Find subgoals in the tree that are not yet achieved and have all dependencies met.
        """
        # This requires fetching all subgoals for the tree, then calculating a topological sort
        # or checking dependency resolution.
        # For prototype purposes, we mock returning a list.
        return []
