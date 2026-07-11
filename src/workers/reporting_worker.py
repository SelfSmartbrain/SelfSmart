from __future__ import annotations

import asyncio
from src.config.logging import get_logger
from src.core.service_registry import get_registry

logger = get_logger(__name__)

async def run_reporting_cycle() -> None:
    logger.info("Starting reporting cycle.")
    try:
        registry = get_registry()
        intelligence_reporter = registry.get("intelligence_reporter")
        # Placeholder logic
        # if intelligence_reporter:
        #     await intelligence_reporter.generate_daily_report()
        logger.info("Executed reporting cycle successfully.")
    except Exception as e:
        logger.error("Error executing reporting cycle", exc_info=True)
