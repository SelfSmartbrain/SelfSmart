from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from src.config.logging import get_logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = get_logger(__name__)

class EvolutionMetrics(BaseModel):
    model_config = {"from_attributes": True}
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    best_fitness: float
    average_fitness: float
    diversity_score: float

class LongHorizonEvolutionTracker:
    def __init__(self):
        self.history: List[EvolutionMetrics] = []
        self.goals: Dict[str, float] = {}
        self.scheduler = AsyncIOScheduler()
        
    async def start_tracking(self) -> None:
        logger.info("Starting long horizon tracking...")
        self.scheduler.start()
        # Schedule periodic reviews
        self.scheduler.add_job(self.review_24h, 'interval', hours=24, id='review_24h')
        self.scheduler.add_job(self.review_72h, 'interval', hours=72, id='review_72h')
        self.scheduler.add_job(self.review_7d, 'interval', days=7, id='review_7d')

    async def stop_tracking(self) -> None:
        logger.info("Stopping long horizon tracking.")
        self.scheduler.shutdown()

    async def record_metrics(self, best: float, avg: float, diversity: float) -> None:
        metrics = EvolutionMetrics(
            best_fitness=best,
            average_fitness=avg,
            diversity_score=diversity
        )
        self.history.append(metrics)
        logger.debug(f"Recorded metrics: best={best}, avg={avg}")

    async def set_goal(self, name: str, target: float) -> None:
        self.goals[name] = target
        logger.info(f"Set long horizon goal '{name}' to {target}")

    async def _get_window_metrics(self, hours: int) -> List[EvolutionMetrics]:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [m for m in self.history if m.timestamp >= cutoff]

    async def review_24h(self) -> None:
        logger.info("Running 24h evolution review...")
        recent = await self._get_window_metrics(24)
        await self._analyze_trend(recent, "24h")

    async def review_72h(self) -> None:
        logger.info("Running 72h evolution review...")
        recent = await self._get_window_metrics(72)
        await self._analyze_trend(recent, "72h")

    async def review_7d(self) -> None:
        logger.info("Running 7d evolution review...")
        recent = await self._get_window_metrics(24 * 7)
        await self._analyze_trend(recent, "7d")

    async def _analyze_trend(self, metrics: List[EvolutionMetrics], window_name: str) -> None:
        if not metrics:
            logger.warning(f"No metrics available for {window_name} review.")
            return
            
        start_fitness = metrics[0].best_fitness
        end_fitness = metrics[-1].best_fitness
        improvement = end_fitness - start_fitness
        
        logger.info(f"[{window_name} Review] Improvement: {improvement:.2f}")
