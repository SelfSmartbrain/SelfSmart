"""pareto_optimizer.py

Pareto optimization for multi-objective decision-making.
Finds Pareto-optimal solutions where no objective can be improved without worsening another.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from src.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Objective:
    """An objective to optimize."""
    name: str
    weight: float = 1.0
    maximize: bool = True  # True for maximization, False for minimization
    target: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "weight": self.weight,
            "maximize": self.maximize,
            "target": self.target,
        }


@dataclass
class Solution:
    """A potential solution with objective values."""
    id: str
    values: Dict[str, float]  # objective_name -> value
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "values": self.values,
            "metadata": self.metadata,
        }
    
    def dominates(self, other: 'Solution', objectives: List[Objective]) -> bool:
        """Check if this solution dominates another."""
        at_least_one_better = False
        
        for obj in objectives:
            self_value = self.values.get(obj.name, 0.0)
            other_value = other.values.get(obj.name, 0.0)
            
            if obj.maximize:
                if self_value < other_value:
                    return False  # Doesn't dominate
                if self_value > other_value:
                    at_least_one_better = True
            else:  # minimize
                if self_value > other_value:
                    return False  # Doesn't dominate
                if self_value < other_value:
                    at_least_one_better = True
        
        return at_least_one_better


class ParetoOptimizer:
    """Finds Pareto-optimal solutions for multi-objective optimization."""
    
    def __init__(self):
        self.objectives: List[Objective] = []
        self.solutions: List[Solution] = []
        logger.info("ParetoOptimizer initialized")
    
    def add_objective(self, objective: Objective) -> None:
        """Add an objective to optimize."""
        self.objectives.append(objective)
        logger.info(f"Added objective: {objective.name}")
    
    def add_solution(self, solution: Solution) -> None:
        """Add a potential solution."""
        self.solutions.append(solution)
        logger.info(f"Added solution: {solution.id}")
    
    def find_pareto_front(self) -> List[Solution]:
        """Find the Pareto-optimal front."""
        if not self.solutions:
            return []
        
        pareto_front = []
        
        for solution in self.solutions:
            is_dominated = False
            
            for other in self.solutions:
                if solution.id == other.id:
                    continue
                
                if other.dominates(solution, self.objectives):
                    is_dominated = True
                    break
            
            if not is_dominated:
                pareto_front.append(solution)
        
        logger.info(f"Found {len(pareto_front)} Pareto-optimal solutions")
        return pareto_front
    
    def rank_solutions(self) -> List[Tuple[Solution, int]]:
        """Rank solutions using Pareto ranking (non-dominated sorting)."""
        if not self.solutions:
            return []
        
        # Simple implementation: assign ranks based on domination
        ranks = []
        remaining = self.solutions.copy()
        current_rank = 1
        
        while remaining:
            # Find current front
            current_front = []
            for solution in remaining:
                is_dominated = False
                for other in remaining:
                    if solution.id == other.id:
                        continue
                    if other.dominates(solution, self.objectives):
                        is_dominated = True
                        break
                if not is_dominated:
                    current_front.append(solution)
            
            # Assign rank
            for solution in current_front:
                ranks.append((solution, current_rank))
            
            # Remove current front from remaining
            remaining = [s for s in remaining if s not in current_front]
            current_rank += 1
        
        return sorted(ranks, key=lambda x: x[1])
    
    def calculate_hypervolume(
        self,
        pareto_front: List[Solution],
        reference_point: Optional[Dict[str, float]] = None,
    ) -> float:
        """Calculate hypervolume indicator for Pareto front."""
        if not pareto_front:
            return 0.0
        
        if not self.objectives:
            return 0.0
        
        # Set reference point if not provided
        if reference_point is None:
            reference_point = {}
            for obj in self.objectives:
                if obj.maximize:
                    reference_point[obj.name] = 0.0
                else:
                    reference_point[obj.name] = 1.0
        
        # Simple hypervolume calculation for 2 objectives
        if len(self.objectives) == 2:
            obj1, obj2 = self.objectives[0], self.objectives[1]
            ref1, ref2 = reference_point[obj1.name], reference_point[obj2.name]
            
            volume = 0.0
            sorted_front = sorted(
                pareto_front,
                key=lambda s: s.values.get(obj1.name, 0.0),
                reverse=obj1.maximize,
            )
            
            for i, solution in enumerate(sorted_front):
                val1 = solution.values.get(obj1.name, 0.0)
                val2 = solution.values.get(obj2.name, 0.0)
                
                if obj1.maximize:
                    width = val1 - ref1
                else:
                    width = ref1 - val1
                
                if obj2.maximize:
                    height = val2 - ref2
                else:
                    height = ref2 - val2
                
                # For subsequent solutions, only count the improvement
                if i > 0:
                    prev_val2 = sorted_front[i - 1].values.get(obj2.name, 0.0)
                    if obj2.maximize:
                        height = max(0.0, val2 - max(prev_val2, ref2))
                    else:
                        height = max(0.0, min(prev_val2, ref2) - val2)
                
                volume += width * height
            
            return max(0.0, volume)
        
        # For more than 2 objectives, return a simplified metric
        return len(pareto_front)
    
    def select_solution(
        self,
        pareto_front: List[Solution],
        preference_weights: Optional[Dict[str, float]] = None,
    ) -> Optional[Solution]:
        """Select a solution from Pareto front using preference weights."""
        if not pareto_front:
            return None
        
        if preference_weights is None:
            # Use objective weights
            preference_weights = {obj.name: obj.weight for obj in self.objectives}
        
        best_solution = None
        best_score = -float("inf")
        
        for solution in pareto_front:
            score = 0.0
            for obj in self.objectives:
                value = solution.values.get(obj.name, 0.0)
                weight = preference_weights.get(obj.name, obj.weight)
                
                if obj.maximize:
                    score += value * weight
                else:
                    score += (1.0 - value) * weight
            
            if score > best_score:
                best_score = score
                best_solution = solution
        
        return best_solution
    
    def get_compromise_solution(self) -> Optional[Solution]:
        """Get a compromise solution using weighted sum."""
        if not self.solutions:
            return None
        
        best_solution = None
        best_score = -float("inf")
        
        for solution in self.solutions:
            score = 0.0
            for obj in self.objectives:
                value = solution.values.get(obj.name, 0.0)
                if obj.maximize:
                    score += value * obj.weight
                else:
                    score += (1.0 - value) * obj.weight
            
            if score > best_score:
                best_score = score
                best_solution = solution
        
        return best_solution
    
    def clear_solutions(self) -> None:
        """Clear all solutions."""
        self.solutions = []
        logger.info("Cleared all solutions")
    
    def clear_objectives(self) -> None:
        """Clear all objectives."""
        self.objectives = []
        logger.info("Cleared all objectives")
