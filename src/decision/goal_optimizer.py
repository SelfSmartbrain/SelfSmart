"""goal_optimizer.py

Optimizes goals and objectives across multiple dimensions.
Balances conflicting goals and finds optimal tradeoffs.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from src.config.logging import get_logger
from src.decision.strategy_engine import StrategicGoal, TimeHorizon, ObjectivePriority

logger = get_logger(__name__)


@dataclass
class GoalConflict:
    """Represents a conflict between goals."""
    goal1_id: str
    goal2_id: str
    conflict_type: str  # resource, time, priority
    severity: float  # 0.0 to 1.0
    description: str = ""


@dataclass
class OptimizationResult:
    """Result of goal optimization."""
    optimized_goals: List[StrategicGoal]
    total_utility: float
    conflicts_resolved: int
    tradeoffs_made: List[str]
    metadata: Dict[str, Any]


class GoalOptimizer:
    """Optimizes goals to maximize overall utility."""
    
    def __init__(self):
        self.conflicts: List[GoalConflict] = []
        logger.info("GoalOptimizer initialized")
    
    def optimize_goals(
        self,
        goals: List[StrategicGoal],
        constraints: Dict[str, Any],
    ) -> OptimizationResult:
        """Optimize a set of goals given constraints."""
        logger.info(f"Optimizing {len(goals)} goals")
        
        # Identify conflicts
        self.conflicts = self._identify_conflicts(goals)
        
        # Calculate initial utility
        initial_utility = self._calculate_total_utility(goals)
        
        # Optimize
        optimized_goals = self._perform_optimization(goals, constraints)
        
        # Calculate final utility
        final_utility = self._calculate_total_utility(optimized_goals)
        
        # Track tradeoffs
        tradeoffs = self._identify_tradeoffs(goals, optimized_goals)
        
        result = OptimizationResult(
            optimized_goals=optimized_goals,
            total_utility=final_utility,
            conflicts_resolved=len(self.conflicts),
            tradeoffs_made=tradeoffs,
            metadata={
                "initial_utility": initial_utility,
                "utility_improvement": final_utility - initial_utility,
                "conflicts_detected": len(self.conflicts),
            },
        )
        
        logger.info(f"Optimization complete. Utility: {initial_utility:.2f} -> {final_utility:.2f}")
        return result
    
    def _identify_conflicts(self, goals: List[StrategicGoal]) -> List[GoalConflict]:
        """Identify conflicts between goals."""
        conflicts = []
        
        for i, goal1 in enumerate(goals):
            for goal2 in goals[i + 1:]:
                conflict = self._check_goal_conflict(goal1, goal2)
                if conflict:
                    conflicts.append(conflict)
        
        return conflicts
    
    def _check_goal_conflict(
        self,
        goal1: StrategicGoal,
        goal2: StrategicGoal,
    ) -> Optional[GoalConflict]:
        """Check if two goals conflict."""
        # Check for deadline conflicts
        if goal1.deadline and goal2.deadline:
            time_diff = abs((goal1.deadline - goal2.deadline).total_seconds())
            if time_diff < 86400:  # Within 1 day
                return GoalConflict(
                    goal1_id=goal1.id,
                    goal2_id=goal2.id,
                    conflict_type="time",
                    severity=0.7,
                    description="Goals have overlapping deadlines",
                )
        
        # Check for priority conflicts (both high priority with limited resources)
        if (goal1.priority in [ObjectivePriority.CRITICAL, ObjectivePriority.HIGH] and
            goal2.priority in [ObjectivePriority.CRITICAL, ObjectivePriority.HIGH]):
            return GoalConflict(
                goal1_id=goal1.id,
                goal2_id=goal2.id,
                conflict_type="priority",
                severity=0.5,
                description="Both goals are high priority",
            )
        
        return None
    
    def _calculate_total_utility(self, goals: List[StrategicGoal]) -> float:
        """Calculate total utility of goals."""
        priority_weights = {
            ObjectivePriority.CRITICAL: 1.0,
            ObjectivePriority.HIGH: 0.8,
            ObjectivePriority.MEDIUM: 0.6,
            ObjectivePriority.LOW: 0.4,
        }
        
        total = 0.0
        for goal in goals:
            weight = priority_weights.get(goal.priority, 0.5)
            # Utility = priority * (1 - estimated_effort / 100)
            effort_penalty = min(1.0, goal.estimated_effort / 100.0)
            utility = weight * (1.0 - effort_penalty)
            total += utility
        
        return total
    
    def _perform_optimization(
        self,
        goals: List[StrategicGoal],
        constraints: Dict[str, Any],
    ) -> List[StrategicGoal]:
        """Perform optimization using mathematical optimization."""
        # This is a simplified version - in practice, would use more sophisticated methods
        
        optimized = []
        
        # Sort by priority
        priority_order = {
            ObjectivePriority.CRITICAL: 0,
            ObjectivePriority.HIGH: 1,
            ObjectivePriority.MEDIUM: 2,
            ObjectivePriority.LOW: 3,
        }
        
        sorted_goals = sorted(goals, key=lambda g: priority_order.get(g.priority, 99))
        
        # Apply constraints
        total_effort_budget = constraints.get("total_effort", 1000.0)
        used_effort = 0.0
        
        for goal in sorted_goals:
            if used_effort + goal.estimated_effort <= total_effort_budget:
                optimized.append(goal)
                used_effort += goal.estimated_effort
            else:
                # Reduce effort for lower priority goals
                remaining_effort = total_effort_budget - used_effort
                if remaining_effort > 0:
                    # Create a modified goal with reduced effort
                    modified_goal = StrategicGoal(
                        id=goal.id,
                        description=goal.description,
                        horizon=goal.horizon,
                        priority=goal.priority,
                        success_criteria=goal.success_criteria,
                        dependencies=goal.dependencies,
                        estimated_effort=remaining_effort,
                        deadline=goal.deadline,
                        progress=goal.progress,
                        metadata=goal.metadata,
                    )
                    optimized.append(modified_goal)
                    used_effort += remaining_effort
        
        return optimized
    
    def _identify_tradeoffs(
        self,
        original: List[StrategicGoal],
        optimized: List[StrategicGoal],
    ) -> List[str]:
        """Identify tradeoffs made during optimization."""
        tradeoffs = []
        
        original_ids = {g.id for g in original}
        optimized_ids = {g.id for g in optimized}
        
        removed = original_ids - optimized_ids
        for goal_id in removed:
            goal = next(g for g in original if g.id == goal_id)
            tradeoffs.append(f"Removed goal: {goal.description}")
        
        # Check for effort reductions
        for opt_goal in optimized:
            orig_goal = next((g for g in original if g.id == opt_goal.id), None)
            if orig_goal and opt_goal.estimated_effort < orig_goal.estimated_effort:
                reduction = orig_goal.estimated_effort - opt_goal.estimated_effort
                tradeoffs.append(
                    f"Reduced effort for '{opt_goal.description}' by {reduction:.1f} hours"
                )
        
        return tradeoffs
    
    def suggest_goal_prioritization(
        self,
        goals: List[StrategicGoal],
        available_resources: Dict[str, float],
    ) -> List[Tuple[StrategicGoal, float]]:
        """Suggest prioritization of goals based on resources."""
        scored_goals = []
        
        for goal in goals:
            score = self._calculate_goal_score(goal, available_resources)
            scored_goals.append((goal, score))
        
        # Sort by score (descending)
        scored_goals.sort(key=lambda x: x[1], reverse=True)
        
        return scored_goals
    
    def _calculate_goal_score(
        self,
        goal: StrategicGoal,
        resources: Dict[str, float],
    ) -> float:
        """Calculate a score for a goal."""
        priority_scores = {
            ObjectivePriority.CRITICAL: 1.0,
            ObjectivePriority.HIGH: 0.8,
            ObjectivePriority.MEDIUM: 0.6,
            ObjectivePriority.LOW: 0.4,
        }
        
        priority_score = priority_scores.get(goal.priority, 0.5)
        effort_score = 1.0 / (1.0 + goal.estimated_effort / 10.0)
        
        # Check if goal fits within resources
        resource_fit = 1.0
        if goal.estimated_effort > resources.get("time", 100):
            resource_fit = 0.5
        
        return priority_score * effort_score * resource_fit
    
    def find_pareto_optimal_goals(
        self,
        goals: List[StrategicGoal],
    ) -> List[StrategicGoal]:
        """Find Pareto-optimal goals (goals that are not dominated)."""
        if not goals:
            return []
        
        pareto_optimal = []
        
        for i, goal1 in enumerate(goals):
            is_dominated = False
            
            for j, goal2 in enumerate(goals):
                if i == j:
                    continue
                
                # Check if goal2 dominates goal1
                # (higher priority and lower effort)
                priority_order = {
                    ObjectivePriority.CRITICAL: 4,
                    ObjectivePriority.HIGH: 3,
                    ObjectivePriority.MEDIUM: 2,
                    ObjectivePriority.LOW: 1,
                }
                
                if (priority_order.get(goal2.priority, 0) >= priority_order.get(goal1.priority, 0) and
                    goal2.estimated_effort <= goal1.estimated_effort and
                    (priority_order.get(goal2.priority, 0) > priority_order.get(goal1.priority, 0) or
                     goal2.estimated_effort < goal1.estimated_effort)):
                    is_dominated = True
                    break
            
            if not is_dominated:
                pareto_optimal.append(goal1)
        
        return pareto_optimal
