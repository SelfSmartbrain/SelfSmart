from __future__ import annotations

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.config.logging import get_logger
from src.workers.research_loop_worker import run_research_loop_cycle
from src.workers.reflection_worker import run_reflection_cycle
from src.workers.meta_learning_worker import run_meta_learning_cycle
from src.workers.skill_discovery_worker import run_skill_discovery_cycle
from src.workers.optimization_worker import run_optimization_cycle
from src.workers.reporting_worker import run_reporting_cycle

logger = get_logger(__name__)

class WorkerScheduler:
    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()
        self._register_jobs()

    def _register_jobs(self) -> None:
        self.scheduler.add_job(run_research_loop_cycle, 'interval', minutes=5, id='research_loop_cycle', replace_existing=True)
        self.scheduler.add_job(run_reflection_cycle, 'interval', hours=1, id='reflection_cycle', replace_existing=True)
        self.scheduler.add_job(run_meta_learning_cycle, 'interval', hours=6, id='meta_learning_cycle', replace_existing=True)
        self.scheduler.add_job(run_skill_discovery_cycle, 'interval', hours=24, id='skill_discovery_cycle', replace_existing=True)
        self.scheduler.add_job(run_optimization_cycle, 'interval', hours=168, id='optimization_cycle', replace_existing=True)
        self.scheduler.add_job(run_reporting_cycle, 'interval', hours=24, id='reporting_cycle', replace_existing=True)
        logger.info("Registered all background worker jobs.")

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Worker scheduler started.")

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Worker scheduler stopped.")

scheduler = WorkerScheduler()
