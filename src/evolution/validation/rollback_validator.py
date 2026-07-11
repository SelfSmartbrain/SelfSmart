from __future__ import annotations
from src.config.logging import get_logger

logger = get_logger(__name__)

class RollbackValidator:
    @staticmethod
    async def validate_rollback_state(deployment_status: str, failure_rate: float) -> bool:
        logger.info("Validating rollback state")
        if deployment_status == "rolled_back":
            logger.warning("Deployment is already rolled back")
            return False
        if failure_rate < 0 or failure_rate > 1:
            logger.error("Failure rate must be between 0 and 1")
            return False
        return True
