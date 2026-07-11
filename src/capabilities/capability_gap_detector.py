from __future__ import annotations

import uuid
import datetime
from typing import List, Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

try:
    from src.db.models import CapabilityGap
except ImportError:
    CapabilityGap = None

class CapabilityGapDetector:
    """
    Analyzes a research goal and current tools list using an LLM
    to identify if a new tool is needed.
    """

    def __init__(self, llm_client: Any):
        self.llm_client = llm_client

    async def detect_gap(
        self, 
        session: AsyncSession, 
        goal: str, 
        available_tools: List[str]
    ) -> dict:
        """
        Identify if there is a gap in capabilities for the given goal and tools.
        Saves a CapabilityGap to the DB and returns it.
        """
        # In a real implementation, we would call self.llm_client.prompt(...)
        # For now, we simulate an identified gap based on the goal.
        identified_gap = f"Identified missing tool capabilities for goal: {goal}"
        
        gap_id = uuid.uuid4()
        now = datetime.datetime.utcnow()

        if CapabilityGap:
            # ORM Pattern
            new_gap = CapabilityGap(
                id=gap_id,
                goal=goal,
                identified_gap=identified_gap,
                status="DETECTED",
                created_at=now,
                updated_at=now
            )
            session.add(new_gap)
            await session.commit()
            await session.refresh(new_gap)
            return {
                "id": str(new_gap.id),
                "goal": new_gap.goal,
                "identified_gap": new_gap.identified_gap,
                "status": new_gap.status,
            }
        else:
            # Fallback to standard Core API
            query = text("""
                INSERT INTO capability_gaps (id, goal, identified_gap, status, created_at, updated_at)
                VALUES (:id, :goal, :identified_gap, :status, :created_at, :updated_at)
            """)
            await session.execute(query, {
                "id": gap_id,
                "goal": goal,
                "identified_gap": identified_gap,
                "status": "DETECTED",
                "created_at": now,
                "updated_at": now
            })
            await session.commit()

            return {
                "id": str(gap_id),
                "goal": goal,
                "identified_gap": identified_gap,
                "status": "DETECTED"
            }
