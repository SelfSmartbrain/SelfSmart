from __future__ import annotations

from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class Critique(BaseModel):
    model_config = {"from_attributes": True}
    
    critique_id: UUID = Field(default_factory=uuid4)
    target_hypothesis_id: UUID
    flaws_identified: List[str]
    evidence_strength: float
    replicability_score: float
    comments: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CriticAgent(BaseModel):
    model_config = {"from_attributes": True}
    
    agent_id: UUID = Field(default_factory=uuid4)
    name: str = "Critic"

    async def evaluate_hypothesis(self, hypothesis_id: UUID, content: str, evidence: List[str]) -> Critique:
        logger.info(f"Critic agent {self.agent_id} evaluating hypothesis {hypothesis_id}")
        
        evidence_strength = min(1.0, len(evidence) * 0.2)
        replicability = 0.8 if len(evidence) > 2 else 0.4
        flaws = []
        
        if evidence_strength < 0.5:
            flaws.append("Insufficient evidence provided.")
            
        return Critique(
            target_hypothesis_id=hypothesis_id,
            flaws_identified=flaws,
            evidence_strength=evidence_strength,
            replicability_score=replicability,
            comments="Evaluation complete."
        )
