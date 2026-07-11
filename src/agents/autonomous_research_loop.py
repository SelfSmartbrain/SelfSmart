"""Autonomous Research Loop."""

from __future__ import annotations

import logging

from src.meta.knowledge_gap_detector import KnowledgeGapDetector
from src.meta.curiosity_engine import CuriosityEngine
from src.agents.goal_generator import GoalGenerator
from src.agents.research_director import ResearchDirector
from src.agents.planner_v2 import LongHorizonPlanner
from src.knowledge_graph.manager import KnowledgeGraphManager

logger = logging.getLogger(__name__)


class AutonomousResearchLoop:
    """
    Top-level orchestration loop that runs continuously to drive autonomous research.
    
    Workflow:
    Detect Gap -> Generate Goal -> Prioritize -> Plan -> Execute -> Update KG -> Evaluate -> Repeat
    """

    def __init__(
        self,
        gap_detector: KnowledgeGapDetector,
        curiosity_engine: CuriosityEngine,
        goal_generator: GoalGenerator,
        director: ResearchDirector,
        planner: LongHorizonPlanner,
        kg_manager: KnowledgeGraphManager,
    ) -> None:
        self.gap_detector = gap_detector
        self.curiosity_engine = curiosity_engine
        self.goal_generator = goal_generator
        self.director = director
        self.planner = planner
        self.kg_manager = kg_manager

    async def run_cycle(self) -> None:
        """Run a single iteration of the autonomous research loop."""
        logger.info("Starting Autonomous Research Cycle")
        
        # 1. Detect Gaps
        gaps = await self.gap_detector.detect_gaps()
        if not gaps:
            logger.info("No gaps detected. Idling.")
            return

        # 2. Score Gaps & Generate Goals
        for gap_data in gaps:
            score = await self.curiosity_engine.evaluate_gap(gap_data)
            if score > 0.6:  # Curiosity threshold
                from src.db.models import KnowledgeGap
                import uuid6
                
                # In reality we would fetch the gap object, here we mock it for the loop
                mock_gap = KnowledgeGap(
                    id=uuid6.uuid7(),
                    domain=gap_data.get("domain", "unknown"),
                    description=gap_data.get("description", "unknown"),
                    importance=gap_data.get("importance", 0.5),
                    confidence=gap_data.get("confidence", 0.5)
                )
                
                goal = await self.goal_generator.generate_from_gap(mock_gap, score)
                
                # 3. Prioritize via Director
                if goal:
                    track = await self.director.evaluate_goal_for_track(goal)
                    
                    # 4. Plan Research
                    if track:
                        await self.planner.create_plan(goal)
                        # Execution would be handed off to the main OrchestratorAgent via LangGraph
        
        # 5. Evaluate results (Review tracks)
        await self.director.review_active_tracks()
        logger.info("Finished Autonomous Research Cycle")
