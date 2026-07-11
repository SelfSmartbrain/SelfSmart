from __future__ import annotations

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class Individual(BaseModel):
    model_config = {"from_attributes": True}
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    genome: Dict[str, Any]
    fitness_score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    generation: int

class PopulationManager:
    def __init__(self, population_size: int):
        self.population_size = population_size
        self.population: List[Individual] = []

    async def initialize_population(self, generation: int = 0) -> None:
        logger.info(f"Initializing population of size {self.population_size}")
        self.population = []
        for _ in range(self.population_size):
            individual = Individual(
                genome={"param_a": 0.5, "param_b": 1.0}, # placeholder genome
                generation=generation
            )
            self.population.append(individual)
            
    async def get_population(self) -> List[Individual]:
        return self.population

    async def update_individual_fitness(self, individual_id: uuid.UUID, fitness: float) -> None:
        for ind in self.population:
            if ind.id == individual_id:
                ind.fitness_score = fitness
                logger.debug(f"Updated fitness for {individual_id}: {fitness}")
                return
        logger.warning(f"Individual {individual_id} not found.")

    async def set_next_generation(self, new_population: List[Individual]) -> None:
        self.population = new_population
        logger.info(f"Population replaced with {len(new_population)} new individuals.")
