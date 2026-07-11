from __future__ import annotations

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class AgentPerformance(BaseModel):
    model_config = {"from_attributes": True}
    
    agent_id: UUID
    tasks_completed: int
    success_rate: float
    collaboration_score: float

class SocietyEvaluationResult(BaseModel):
    model_config = {"from_attributes": True}
    
    evaluation_id: UUID = Field(default_factory=uuid4)
    collective_intelligence_score: float
    synergy_index: float
    agent_performances: List[AgentPerformance]
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SocietyEvaluator(BaseModel):
    model_config = {"from_attributes": True}
    
    async def evaluate_society(self, agents_data: List[Dict[str, Any]]) -> SocietyEvaluationResult:
        logger.info("Evaluating society of agents for collective intelligence.")
        
        performances = []
        total_success = 0.0
        total_collaboration = 0.0
        
        for data in agents_data:
            perf = AgentPerformance(
                agent_id=data.get("agent_id", uuid4()),
                tasks_completed=data.get("tasks_completed", 0),
                success_rate=data.get("success_rate", 0.0),
                collaboration_score=data.get("collaboration_score", 0.0)
            )
            performances.append(perf)
            total_success += perf.success_rate
            total_collaboration += perf.collaboration_score
            
        num_agents = len(agents_data) if agents_data else 1
        avg_success = total_success / num_agents
        avg_collab = total_collaboration / num_agents
        
        # Synergistic effect boosts CI score
        synergy_index = avg_collab * 1.2
        ci_score = min(1.0, (avg_success * 0.6) + (synergy_index * 0.4))
        
        result = SocietyEvaluationResult(
            collective_intelligence_score=ci_score,
            synergy_index=synergy_index,
            agent_performances=performances
        )
        
        logger.info(f"Society evaluation complete. CI Score: {ci_score}")
        return result
