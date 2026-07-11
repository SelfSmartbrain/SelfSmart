from __future__ import annotations

import asyncio
import logging

from src.config.logging import get_logger
from tests.e2e.projects.real_world_autonomy_test import run_real_world_autonomy_test

logger = get_logger(__name__)

async def run_long_horizon_testing(iterations: int = 5, delay_between_runs: float = 2.0):
    """
    Script to loop long horizon testing of the autonomy capabilities.
    """
    logger.info(f"Starting Long Horizon Autonomy Runner for {iterations} iterations.")
    
    for i in range(1, iterations + 1):
        logger.info(f"--- Starting Iteration {i}/{iterations} ---")
        try:
            await run_real_world_autonomy_test()
            logger.info(f"--- Iteration {i} Successful ---")
        except Exception as e:
            logger.error(f"--- Iteration {i} Failed: {str(e)} ---")
            # In a real long-horizon test, we might decide whether to break or continue
            logger.warning("Continuing to next iteration despite failure...")
            
        if i < iterations:
            logger.info(f"Waiting for {delay_between_runs} seconds before next iteration...")
            await asyncio.sleep(delay_between_runs)

    logger.info("Long Horizon Autonomy Runner completed all iterations.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Run 3 iterations for demonstration purposes
    asyncio.run(run_long_horizon_testing(iterations=3, delay_between_runs=1.0))
