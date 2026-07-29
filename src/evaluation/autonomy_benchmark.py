from __future__ import annotations
from typing import Dict, Any, Optional
import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from src.config.logging import get_logger
from src.db.models import Execution

logger = get_logger(__name__)


class BenchmarkRun(BaseModel):
    id: uuid.UUID
    agent_id: str
    successful_autonomous_actions: int
    total_actions: int
    autonomy_score: float
    timestamp: datetime
    model_config = {"from_attributes": True}


class AutonomyBenchmark:
    """Benchmark framework to calculate Autonomy Score."""

    def __init__(self) -> None:
        self.logger = logger

    async def evaluate(
        self,
        db: AsyncSession,
        agent_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculates autonomy score (Successful Autonomous Actions / Total Actions).

        Queries the database for actual execution records within the specified time range
        and calculates the ratio of successful autonomous actions to total actions.
        """
        self.logger.info(f"Evaluating autonomy benchmark for agent {agent_id}")

        # Build time filter
        time_filter = []
        if start_time:
            time_filter.append(Execution.created_at >= start_time)
        if end_time:
            time_filter.append(Execution.created_at <= end_time)

        # Query total actions for this agent
        base_conditions = [Execution.agent_id == agent_id]
        if time_filter:
            base_conditions.extend(time_filter)

        total_actions_query = select(func.count(Execution.id)).where(and_(*base_conditions))

        total_actions_result = await db.execute(total_actions_query)
        total_actions = total_actions_result.scalar() or 0

        # Query successful autonomous actions
        # An action is considered autonomous if it was initiated by the agent
        # and successful if it completed without errors
        success_conditions = [
            Execution.agent_id == agent_id,
            Execution.status == "completed",
            Execution.error.is_(None),
        ]
        if time_filter:
            success_conditions.extend(time_filter)

        successful_actions_query = select(func.count(Execution.id)).where(and_(*success_conditions))

        successful_actions_result = await db.execute(successful_actions_query)
        successful_actions = successful_actions_result.scalar() or 0

        # Calculate autonomy score
        score = successful_actions / total_actions if total_actions > 0 else 0.0

        self.logger.info(
            f"Autonomy benchmark results for agent {agent_id}: "
            f"{successful_actions}/{total_actions} successful actions "
            f"(score: {score:.2%})"
        )

        run = BenchmarkRun(
            id=uuid.uuid4(),
            agent_id=agent_id,
            successful_autonomous_actions=successful_actions,
            total_actions=total_actions,
            autonomy_score=score,
            timestamp=datetime.utcnow(),
        )

        return run.model_dump()
