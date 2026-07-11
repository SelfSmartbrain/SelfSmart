from __future__ import annotations

from typing import List, Optional, Dict
from uuid import UUID, uuid4
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.review.critic_agent import CriticAgent, Critique
from src.review.verification_agent import VerificationAgent, VerificationResult
from src.review.challenge_generator import ChallengeGenerator, Challenge

logger = get_logger(__name__)

class ReviewCycleResult(BaseModel):
    model_config = {"from_attributes": True}
    
    cycle_id: UUID = Field(default_factory=uuid4)
    hypothesis_id: UUID
    critique: Critique
    challenges: List[Challenge]
    verification: VerificationResult
    status: str
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PeerReviewEngine(BaseModel):
    model_config = {"from_attributes": True}
    
    critic: CriticAgent = Field(default_factory=CriticAgent)
    verifier: VerificationAgent = Field(default_factory=VerificationAgent)
    challenger: ChallengeGenerator = Field(default_factory=ChallengeGenerator)

    async def run_review_cycle(self, hypothesis_id: UUID, content: str, evidence: List[str], methodology: str) -> ReviewCycleResult:
        logger.info(f"Starting peer review cycle for hypothesis {hypothesis_id}")
        
        # 1. Critic evaluates
        critique = await self.critic.evaluate_hypothesis(hypothesis_id, content, evidence)
        
        # 2. Challenge generation based on flaws
        challenge = await self.challenger.generate_challenge(hypothesis_id, critique.flaws_identified)
        
        # 3. Verification attempt
        verification = await self.verifier.verify(hypothesis_id, methodology, critique.replicability_score)
        
        status = "Accepted" if verification.is_verified and critique.evidence_strength > 0.6 else "Needs Revision"
        
        result = ReviewCycleResult(
            hypothesis_id=hypothesis_id,
            critique=critique,
            challenges=[challenge],
            verification=verification,
            status=status
        )
        logger.info(f"Completed peer review cycle. Status: {status}")
        return result
