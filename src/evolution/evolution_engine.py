from __future__ import annotations

import asyncio
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

from src.config.logging import get_logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = get_logger(__name__)

class EvolutionConfig(BaseModel):
    model_config = {"from_attributes": True}
    
    generation_limit: int = 100
    population_size: int = 50
    mutation_rate: float = 0.1
    crossover_rate: float = 0.8
    parallel_benchmark_workers: int = 4

class EvolutionEngine:
    def __init__(self, config: EvolutionConfig):
        self.config = config
        self.scheduler = AsyncIOScheduler()
        self.current_generation: int = 0
        self.is_running: bool = False

    async def start(self) -> None:
        if self.is_running:
            logger.warning("Evolution engine is already running.")
            return
        
        self.is_running = True
        logger.info("Starting evolution engine...")
        self.scheduler.start()
        
        # Schedule the evolutionary loop
        self.scheduler.add_job(self.run_generation, 'interval', seconds=60, id='evolution_loop')

    async def stop(self) -> None:
        if not self.is_running:
            return
            
        logger.info("Stopping evolution engine...")
        self.scheduler.shutdown()
        self.is_running = False

    async def run_generation(self) -> None:
        if self.current_generation >= self.config.generation_limit:
            logger.info("Evolution completed.")
            await self.stop()
            return
            
        logger.info(f"Running generation {self.current_generation}")
        # Run parallel benchmarking step
        await self._run_parallel_benchmarks()
        
        # Increment generation
        self.current_generation += 1
        logger.info(f"Generation {self.current_generation} completed.")

    async def _run_parallel_benchmarks(self) -> None:
        # Simulate parallel benchmarking
        logger.info("Running parallel benchmarks...")
        tasks = []
        for i in range(self.config.parallel_benchmark_workers):
            tasks.append(self._benchmark_worker(i))
            
        await asyncio.gather(*tasks)

    async def _benchmark_worker(self, worker_id: int) -> dict[str, Any]:
        """Benchmark genome candidates using the real evaluator and registry.

        NOTE: GenomeRegistry is DB-backed and requires a session.  When the
        runtime has no DB session available (e.g. integration tests) the worker
        logs a warning and returns an empty result rather than crashing.
        """
        from src.evolution.candidate_evaluator import CandidateEvaluator
        from src.evolution.genome_registry import GenomeRegistry

        try:
            from src.db.session import AsyncSessionLocal
        except ImportError:
            logger.warning(f"Benchmark worker {worker_id}: DB session unavailable, skipping")
            return {"worker_id": worker_id, "evaluated": []}

        results: list[dict[str, Any]] = []
        try:
            async with AsyncSessionLocal() as session:
                registry = GenomeRegistry(session=session)
                evaluator = CandidateEvaluator()

                candidates = await registry.list_active_genomes(limit=5)
                for candidate in candidates:
                    # Build a metrics dict from available genome data
                    genome_data = candidate.genome_data or {}
                    metrics = {
                        "throughput": genome_data.get("throughput", 0.5),
                        "accuracy": genome_data.get("accuracy", 0.5),
                        "error_rate": genome_data.get("error_rate", 0.1),
                    }
                    evaluation = await evaluator.evaluate_candidate(candidate.id, metrics)
                    await registry.update_fitness(candidate.id, evaluation.fitness_score)
                    results.append(
                        {"id": str(candidate.id), "fitness": evaluation.fitness_score}
                    )

            logger.info(f"Benchmark worker {worker_id} evaluated {len(results)} candidates")
        except Exception as exc:
            logger.error(f"Benchmark worker {worker_id} failed: {exc}")

        return {"worker_id": worker_id, "evaluated": results}
