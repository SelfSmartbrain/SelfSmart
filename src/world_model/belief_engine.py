from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class Evidence(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    description: str
    credibility: float = Field(..., ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_config = {"from_attributes": True}

class Belief(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    concept: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_history: List[Evidence] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_config = {"from_attributes": True}

class BeliefUpdateResult(BaseModel):
    belief_id: uuid.UUID
    previous_confidence: float
    new_confidence: float
    status: str
    model_config = {"from_attributes": True}

class BeliefEngine:
    """Manages Bayesian-style belief updates and confidence levels."""

    def __init__(self) -> None:
        self.beliefs: Dict[uuid.UUID, Belief] = {}
        logger.info("BeliefEngine initialized.")

    async def add_belief(self, concept: str, initial_confidence: float = 0.5) -> Belief:
        """Adds a new belief to the engine."""
        logger.info(f"Adding new belief for concept: {concept}")
        belief = Belief(concept=concept, confidence=initial_confidence)
        self.beliefs[belief.id] = belief
        return belief

    async def evaluate_evidence(self, belief_id: uuid.UUID, evidence_desc: str, credibility: float, impact: float) -> BeliefUpdateResult:
        """Evaluates new evidence and updates belief confidence."""
        if belief_id not in self.beliefs:
            logger.error(f"Belief {belief_id} not found.")
            raise ValueError(f"Belief {belief_id} not found.")

        belief = self.beliefs[belief_id]
        evidence = Evidence(description=evidence_desc, credibility=credibility)
        belief.evidence_history.append(evidence)

        prev_confidence = belief.confidence

        # Simple update: impact (e.g. -0.2 to +0.2) scaled by credibility
        adjustment = impact * credibility
        new_confidence = max(0.0, min(1.0, prev_confidence + adjustment))

        belief.confidence = new_confidence
        belief.updated_at = datetime.now(timezone.utc)

        status = "strengthened" if new_confidence > prev_confidence else ("weakened" if new_confidence < prev_confidence else "unchanged")
        if new_confidence == 0.0:
            status = "rejected"
        elif new_confidence == 1.0:
            status = "confirmed"

        logger.info(f"Belief {belief_id} updated: {status} (confidence {prev_confidence:.2f} -> {new_confidence:.2f})")

        return BeliefUpdateResult(
            belief_id=belief.id,
            previous_confidence=prev_confidence,
            new_confidence=new_confidence,
            status=status
        )

    async def get_belief(self, belief_id: uuid.UUID) -> Optional[Belief]:
        """Retrieves a specific belief by ID."""
        return self.beliefs.get(belief_id)

    async def list_beliefs(self) -> List[Belief]:
        """Lists all stored beliefs."""
        return list(self.beliefs.values())
