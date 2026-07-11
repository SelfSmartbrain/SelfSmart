"""strategy_mutator.py

Phase 16F: Strategy Mutator

Mutates and evolves strategies based on performance.
Implements:
- Strategy variation generation
- Strategy crossover
- Strategy selection
"""

from __future__ import annotations

import uuid
import random
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


class MutationType(str, Enum):
    """Types of strategy mutations."""
    PARAMETER_SHIFT = "parameter_shift"
    OBJECTIVE_ADDITION = "objective_addition"
    OBJECTIVE_REMOVAL = "objective_removal"
    CONSTRAINT_RELAXATION = "constraint_relaxation"
    CONSTRAINT_TIGHTENING = "constraint_tightening"
    TIME_HORIZON_SHIFT = "time_horizon_shift"


@dataclass
class StrategyMutation:
    """A mutation applied to a strategy."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    mutation_type: MutationType = MutationType.PARAMETER_SHIFT
    original_strategy: Dict[str, Any] = field(default_factory=dict)
    mutated_strategy: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    expected_impact: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "mutation_type": self.mutation_type.value,
            "original_strategy": self.original_strategy,
            "mutated_strategy": self.mutated_strategy,
            "description": self.description,
            "expected_impact": self.expected_impact,
            "metadata": self.metadata,
        }


class StrategyMutator:
    """Mutates strategies to explore alternatives."""
    
    def __init__(self):
        self.mutations: Dict[str, StrategyMutation] = {}
        self.mutation_history: List[Dict[str, Any]] = []
        logger.info("StrategyMutator initialized")
    
    def generate_mutations(
        self,
        strategy: Dict[str, Any],
        num_mutations: int = 5,
    ) -> List[StrategyMutation]:
        """Generate mutations of a strategy."""
        mutations = []
        
        mutation_types = list(MutationType)
        
        for _ in range(num_mutations):
            mutation_type = random.choice(mutation_types)
            
            mutation = self._apply_mutation(strategy, mutation_type)
            mutations.append(mutation)
            
            self.mutations[mutation.id] = mutation
        
        logger.info(f"Generated {len(mutations)} mutations for strategy")
        
        return mutations
    
    def _apply_mutation(
        self,
        strategy: Dict[str, Any],
        mutation_type: MutationType,
    ) -> StrategyMutation:
        """Apply a specific mutation type to a strategy."""
        mutated_strategy = strategy.copy()
        description = ""
        expected_impact = ""
        
        if mutation_type == MutationType.PARAMETER_SHIFT:
            # Shift a parameter by +/- 10%
            parameters = mutated_strategy.get("parameters", {})
            if parameters:
                param_key = random.choice(list(parameters.keys()))
                old_value = parameters[param_key]
                shift = random.uniform(-0.1, 0.1)
                new_value = old_value * (1 + shift)
                parameters[param_key] = new_value
                
                description = f"Shifted parameter {param_key} from {old_value:.2f} to {new_value:.2f}"
                expected_impact = "May change risk-reward balance"
        
        elif mutation_type == MutationType.OBJECTIVE_ADDITION:
            # Add a new objective
            objectives = mutated_strategy.get("objectives", [])
            new_objectives = [
                "maximize efficiency",
                "minimize cost",
                "maximize quality",
                "minimize time",
                "maximize innovation",
            ]
            new_obj = random.choice([o for o in new_objectives if o not in objectives])
            objectives.append(new_obj)
            
            description = f"Added objective: {new_obj}"
            expected_impact = "May broaden strategy scope"
        
        elif mutation_type == MutationType.OBJECTIVE_REMOVAL:
            # Remove an objective
            objectives = mutated_strategy.get("objectives", [])
            if objectives and len(objectives) > 1:
                removed = random.choice(objectives)
                objectives.remove(removed)
                
                description = f"Removed objective: {removed}"
                expected_impact = "May narrow strategy focus"
        
        elif mutation_type == MutationType.CONSTRAINT_RELAXATION:
            # Relax a constraint
            constraints = mutated_strategy.get("constraints", [])
            if constraints:
                constraint_idx = random.randint(0, len(constraints) - 1)
                constraints.pop(constraint_idx)
                
                description = "Relaxed a constraint"
                expected_impact = "May increase flexibility"
        
        elif mutation_type == MutationType.CONSTRAINT_TIGHTENING:
            # Add a constraint
            constraints = mutated_strategy.get("constraints", [])
            new_constraints = [
                "budget_limit",
                "time_limit",
                "quality_threshold",
                "safety_requirement",
            ]
            new_constraint = random.choice([c for c in new_constraints if c not in constraints])
            constraints.append(new_constraint)
            
            description = f"Added constraint: {new_constraint}"
            expected_impact = "May reduce flexibility but increase quality"
        
        elif mutation_type == MutationType.TIME_HORIZON_SHIFT:
            # Shift time horizon
            horizons = ["short", "medium", "long"]
            current_horizon = mutated_strategy.get("time_horizon", "medium")
            current_idx = horizons.index(current_horizon) if current_horizon in horizons else 1
            
            # Shift to adjacent horizon
            new_idx = max(0, min(len(horizons) - 1, current_idx + random.choice([-1, 1])))
            new_horizon = horizons[new_idx]
            
            mutated_strategy["time_horizon"] = new_horizon
            
            description = f"Shifted time horizon from {current_horizon} to {new_horizon}"
            expected_impact = "May change planning approach"
        
        mutation = StrategyMutation(
            mutation_type=mutation_type,
            original_strategy=strategy,
            mutated_strategy=mutated_strategy,
            description=description,
            expected_impact=expected_impact,
        )
        
        return mutation
    
    def crossover_strategies(
        self,
        strategy1: Dict[str, Any],
        strategy2: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Combine two strategies through crossover."""
        child_strategy = {}
        
        # Crossover parameters
        params1 = strategy1.get("parameters", {})
        params2 = strategy2.get("parameters", {})
        
        if params1 and params2:
            child_parameters = {}
            all_keys = set(params1.keys()) | set(params2.keys())
            
            for key in all_keys:
                if key in params1 and key in params2:
                    # Average the values
                    child_parameters[key] = (params1[key] + params2[key]) / 2
                elif key in params1:
                    child_parameters[key] = params1[key]
                else:
                    child_parameters[key] = params2[key]
            
            child_strategy["parameters"] = child_parameters
        
        # Crossover objectives
        objectives1 = strategy1.get("objectives", [])
        objectives2 = strategy2.get("objectives", [])
        
        child_objectives = list(set(objectives1) | set(objectives2))
        child_strategy["objectives"] = child_objectives
        
        # Crossover time horizon
        horizons = ["short", "medium", "long"]
        h1 = strategy1.get("time_horizon", "medium")
        h2 = strategy2.get("time_horizon", "medium")
        
        if h1 in horizons and h2 in horizons:
            idx1 = horizons.index(h1)
            idx2 = horizons.index(h2)
            child_idx = (idx1 + idx2) // 2
            child_strategy["time_horizon"] = horizons[child_idx]
        
        logger.info("Created strategy crossover")
        
        return child_strategy
    
    def select_best_mutations(
        self,
        mutations: List[StrategyMutation],
        performance_scores: List[float],
        top_k: int = 3,
    ) -> List[StrategyMutation]:
        """Select the best performing mutations."""
        if len(mutations) != len(performance_scores):
            logger.warning("Mutation count and score count mismatch")
            return mutations[:top_k]
        
        # Pair mutations with scores
        scored = list(zip(mutations, performance_scores))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Return top k
        best = [m for m, s in scored[:top_k]]
        
        logger.info(f"Selected top {len(best)} mutations")
        
        return best
    
    def get_mutation(self, mutation_id: str) -> Optional[StrategyMutation]:
        """Get a mutation by ID."""
        return self.mutations.get(mutation_id)
    
    def get_mutation_statistics(self) -> Dict[str, Any]:
        """Get statistics about mutations."""
        total_mutations = len(self.mutations)
        
        by_type = {
            m_type.value: len([m for m in self.mutations.values() if m.mutation_type == m_type])
            for m_type in MutationType
        }
        
        return {
            "total_mutations": total_mutations,
            "by_type": by_type,
        }
