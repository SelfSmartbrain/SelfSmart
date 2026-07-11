from __future__ import annotations

import random
from typing import List, Optional
from uuid import UUID

from src.config.logging import get_logger
from src.evolution.population_manager import Individual

logger = get_logger(__name__)

class SelectionEngine:
    def __init__(self, tournament_size: int = 3, elitism_count: int = 2):
        self.tournament_size = tournament_size
        self.elitism_count = elitism_count

    async def select_parents(self, population: List[Individual], num_parents: int) -> List[Individual]:
        logger.info(f"Selecting {num_parents} parents using tournament selection.")
        parents = []
        for _ in range(num_parents):
            parent = await self._tournament_selection(population)
            if parent:
                parents.append(parent)
        return parents

    async def _tournament_selection(self, population: List[Individual]) -> Optional[Individual]:
        if not population:
            return None
            
        valid_population = [ind for ind in population if ind.fitness_score is not None]
        if not valid_population:
            logger.warning("No individuals with fitness scores found for tournament.")
            return random.choice(population)
            
        tournament = random.sample(
            valid_population, 
            k=min(self.tournament_size, len(valid_population))
        )
        # Higher fitness is better
        tournament.sort(key=lambda x: x.fitness_score, reverse=True)
        return tournament[0]

    async def get_elites(self, population: List[Individual]) -> List[Individual]:
        logger.info(f"Selecting top {self.elitism_count} elites.")
        valid_population = [ind for ind in population if ind.fitness_score is not None]
        valid_population.sort(key=lambda x: x.fitness_score, reverse=True)
        return valid_population[:self.elitism_count]
