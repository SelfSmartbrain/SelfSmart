from __future__ import annotations

from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class Challenge(BaseModel):
    model_config = {"from_attributes": True}
    
    challenge_id: UUID = Field(default_factory=uuid4)
    hypothesis_id: UUID
    description: str
    difficulty_level: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChallengeGenerator(BaseModel):
    model_config = {"from_attributes": True}
    
    generator_id: UUID = Field(default_factory=uuid4)

    async def generate_challenge(self, hypothesis_id: UUID, flaws: List[str]) -> Challenge:
        logger.info(f"Generating challenge for hypothesis {hypothesis_id}")
        
        desc = f"Address the following flaws: {', '.join(flaws)}" if flaws else "Stress test the hypothesis under edge cases."
        difficulty = 0.5 + min(0.5, len(flaws) * 0.1)
        
        return Challenge(
            hypothesis_id=hypothesis_id,
            description=desc,
            difficulty_level=difficulty
        )
