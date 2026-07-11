from __future__ import annotations
from src.config.logging import get_logger

logger = get_logger(__name__)

class PromotionValidator:
    @staticmethod
    async def validate_promotion_criteria(candidate_fitness: float, baseline_fitness: float) -> bool:
        logger.info("Validating promotion criteria")
        if baseline_fitness < 0 or candidate_fitness < 0:
            logger.error("Fitness values cannot be negative")
            return False
        return True
