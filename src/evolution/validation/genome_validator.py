from __future__ import annotations
from typing import Dict, Any
from src.config.logging import get_logger

logger = get_logger(__name__)

class GenomeValidator:
    @staticmethod
    async def validate_genome_structure(genome: Dict[str, Any]) -> bool:
        logger.info("Validating genome structure")
        if "layers" not in genome or not isinstance(genome["layers"], list):
            logger.error("Genome must contain a 'layers' list")
            return False
        if "connections" not in genome or not isinstance(genome["connections"], list):
            logger.error("Genome must contain a 'connections' list")
            return False
        return True
