from __future__ import annotations

import copy
import random
from typing import Any, Dict, List, Tuple
from uuid import UUID

from src.config.logging import get_logger
from src.evolution.cognitive_genome import CognitiveGenomeData

logger = get_logger(__name__)


class GenomeMutator:
    def __init__(self, mutation_rate_multiplier: float = 1.0):
        self.mutation_rate_multiplier = mutation_rate_multiplier

    def mutate(self, genome_data: CognitiveGenomeData) -> Tuple[CognitiveGenomeData, List[Dict[str, Any]]]:
        """Mutate a genome based on its traits' mutation rates."""
        logger.info("Mutating genome data")
        new_genome_data = copy.deepcopy(genome_data)
        mutations = []

        for trait_name, trait in new_genome_data.traits.items():
            eff_rate = trait.mutation_rate * self.mutation_rate_multiplier
            if random.random() < eff_rate:
                old_val = trait.value
                
                if trait.is_categorical and trait.categories:
                    possible = [c for c in trait.categories if c != trait.value]
                    if possible:
                        trait.value = random.choice(possible)
                elif isinstance(trait.value, bool):
                    trait.value = not trait.value
                elif isinstance(trait.value, (int, float)):
                    # simple gaussian mutation
                    delta = random.gauss(0, abs(trait.value) * 0.1 if trait.value != 0 else 0.1)
                    if isinstance(trait.value, int):
                        trait.value += int(round(delta))
                    else:
                        trait.value += delta
                    
                    if trait.min_value is not None:
                        trait.value = max(trait.min_value, trait.value)
                    if trait.max_value is not None:
                        trait.value = min(trait.max_value, trait.value)
                
                if old_val != trait.value:
                    mutations.append({
                        "trait": trait_name,
                        "old_value": old_val,
                        "new_value": trait.value
                    })

        return new_genome_data, mutations

    def crossover(self, parent1: CognitiveGenomeData, parent2: CognitiveGenomeData) -> CognitiveGenomeData:
        """Perform uniform crossover between two genomes."""
        logger.info("Crossing over two genomes")
        child_data = CognitiveGenomeData(
            traits={},
            architecture_config=copy.deepcopy(parent1.architecture_config),
            hyperparameters=copy.deepcopy(parent1.hyperparameters),
            topology_definitions=copy.deepcopy(parent1.topology_definitions)
        )
        
        all_trait_keys = set(parent1.traits.keys()).union(set(parent2.traits.keys()))
        
        for key in all_trait_keys:
            t1 = parent1.traits.get(key)
            t2 = parent2.traits.get(key)
            
            if t1 and t2:
                # 50% chance to inherit from either parent
                chosen = copy.deepcopy(t1) if random.random() < 0.5 else copy.deepcopy(t2)
                child_data.traits[key] = chosen
            elif t1:
                child_data.traits[key] = copy.deepcopy(t1)
            elif t2:
                child_data.traits[key] = copy.deepcopy(t2)
                
        return child_data
