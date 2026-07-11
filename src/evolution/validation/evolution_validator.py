from __future__ import annotations
from typing import Dict, Any
from src.config.logging import get_logger

logger = get_logger(__name__)

class EvolutionValidator:
    @staticmethod
    async def validate_evolution_params(params: Dict[str, Any]) -> bool:
        logger.info("Validating evolution parameters")
        required_keys = ["mutation_rate", "crossover_rate", "population_size"]
        for key in required_keys:
            if key not in params:
                logger.error(f"Missing required parameter: {key}")
                return False
        return True
