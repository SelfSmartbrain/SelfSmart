from __future__ import annotations

from typing import Dict, Any, List, Optional
from uuid import UUID

from src.config.logging import get_logger
from src.evolution.population_manager import Individual

logger = get_logger(__name__)

class FitnessFunction:
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or {"accuracy": 0.5, "latency": -0.3, "resource_usage": -0.2}

    async def evaluate(self, metrics: Dict[str, float]) -> float:
        """
        Evaluate composite fitness based on metrics.
        Higher is better.
        """
        score = 0.0
        for metric, weight in self.weights.items():
            value = metrics.get(metric, 0.0)
            score += value * weight
            
        logger.debug(f"Evaluated fitness score: {score}")
        return score

    async def evaluate_population(self, population: List[Individual], benchmark_results: Dict[UUID, Dict[str, float]]) -> None:
        """
        Apply fitness function to the entire population.
        """
        logger.info(f"Evaluating fitness for {len(population)} individuals.")
        for individual in population:
            metrics = benchmark_results.get(individual.id, {})
            fitness = await self.evaluate(metrics)
            individual.fitness_score = fitness
