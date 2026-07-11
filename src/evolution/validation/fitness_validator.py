from __future__ import annotations
import math
from src.config.logging import get_logger

logger = get_logger(__name__)

class FitnessValidator:
    @staticmethod
    async def validate_fitness_score(score: float) -> bool:
        logger.info("Validating fitness score")
        if math.isnan(score) or math.isinf(score):
            logger.error("Fitness score must be a finite number")
            return False
        return True
