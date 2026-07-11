"""strategy_engine.py

Core strategy engine for high-level strategic planning.
Coordinates strategic thinking across multiple time horizons.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.decision.objective_engine import ObjectiveEngine, Objective, ObjectivePriority

logger = get_logger(__name__)


class TimeHorizon(str, Enum):
    """Time horizons for strategic planning."""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class StrategyStatus(str, Enum):
    """Status of a strategy."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StrategicGoal:
    """A strategic goal at a specific time horizon."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    horizon: TimeHorizon = TimeHorizon.MONTH
    priority: ObjectivePriority = ObjectivePriority.MEDIUM
    success_criteria: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    estimated_effort: float = 1.0  # in hours
    deadline: Optional[datetime] = None
    progress: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "horizon": self.horizon.value,
            "priority": self.priority.value,
            "success_criteria": self.success_criteria,
            "dependencies": self.dependencies,
            "estimated_effort": self.estimated_effort,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "progress": self.progress,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class Strategy:
    """A strategic plan for achieving goals."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    status: StrategyStatus = StrategyStatus.DRAFT
    time_horizon: TimeHorizon = TimeHorizon.MONTH
    goals: List[StrategicGoal] = field(default_factory=list)
    resource_allocation: Dict[str, float] = field(default_factory=dict)
    risk_assessment: Dict[str, float] = field(default_factory=dict)
    success_probability: float = 0.5
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "time_horizon": self.time_horizon.value,
            "goals": [g.to_dict() for g in self.goals],
            "resource_allocation": self.resource_allocation,
            "risk_assessment": self.risk_assessment,
            "success_probability": self.success_probability,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


class StrategyEngine:
    """Core strategy engine for strategic planning."""
    
    def __init__(self, objective_engine: Optional[ObjectiveEngine] = None):
        self.objective_engine = objective_engine or ObjectiveEngine()
        self.strategies: Dict[str, Strategy] = {}
        self.active_strategy_id: Optional[str] = None
        logger.info("StrategyEngine initialized")
    
    def create_strategy(
        self,
        name: str,
        description: str,
        time_horizon: TimeHorizon = TimeHorizon.MONTH,
        goals: Optional[List[StrategicGoal]] = None,
    ) -> Strategy:
        """Create a new strategy."""
        strategy = Strategy(
            name=name,
            description=description,
            time_horizon=time_horizon,
            goals=goals or [],
        )
        
        self.strategies[strategy.id] = strategy
        logger.info(f"Created strategy: {name}")
        return strategy
    
    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """Get a strategy by ID."""
        return self.strategies.get(strategy_id)
    
    def update_strategy(self, strategy_id: str, updates: Dict[str, Any]) -> Optional[Strategy]:
        """Update a strategy."""
        strategy = self.get_strategy(strategy_id)
        if strategy is None:
            return None
        
        for key, value in updates.items():
            if hasattr(strategy, key):
                setattr(strategy, key, value)
        
        strategy.updated_at = datetime.now(timezone.utc)
        logger.info(f"Updated strategy: {strategy_id}")
        return strategy
    
    def activate_strategy(self, strategy_id: str) -> None:
        """Activate a strategy."""
        strategy = self.get_strategy(strategy_id)
        if strategy:
            strategy.status = StrategyStatus.ACTIVE
            self.active_strategy_id = strategy_id
            logger.info(f"Activated strategy: {strategy_id}")
    
    def deactivate_strategy(self, strategy_id: str) -> None:
        """Deactivate a strategy."""
        strategy = self.get_strategy(strategy_id)
        if strategy:
            strategy.status = StrategyStatus.PAUSED
            if self.active_strategy_id == strategy_id:
                self.active_strategy_id = None
            logger.info(f"Deactivated strategy: {strategy_id}")
    
    def add_goal(self, strategy_id: str, goal: StrategicGoal) -> None:
        """Add a goal to a strategy."""
        strategy = self.get_strategy(strategy_id)
        if strategy:
            strategy.goals.append(goal)
            logger.info(f"Added goal to strategy: {strategy_id}")
    
    def remove_goal(self, strategy_id: str, goal_id: str) -> None:
        """Remove a goal from a strategy."""
        strategy = self.get_strategy(strategy_id)
        if strategy:
            strategy.goals = [g for g in strategy.goals if g.id != goal_id]
            logger.info(f"Removed goal from strategy: {strategy_id}")
    
    def assess_strategy(self, strategy_id: str) -> Dict[str, Any]:
        """Assess a strategy's viability and success probability."""
        strategy = self.get_strategy(strategy_id)
        if strategy is None:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        # Calculate success probability based on goals
        if not strategy.goals:
            success_prob = 0.5
        else:
            avg_priority_score = self._calculate_priority_score(strategy.goals)
            resource_adequacy = self._assess_resource_adequacy(strategy)
            risk_factor = self._assess_risk_factor(strategy)
            
            success_prob = avg_priority_score * resource_adequacy * (1.0 - risk_factor)
        
        strategy.success_probability = max(0.0, min(1.0, success_prob))
        strategy.updated_at = datetime.now(timezone.utc)
        
        return {
            "strategy_id": strategy_id,
            "success_probability": strategy.success_probability,
            "assessment": {
                "priority_score": self._calculate_priority_score(strategy.goals),
                "resource_adequacy": self._assess_resource_adequacy(strategy),
                "risk_factor": self._assess_risk_factor(strategy),
            },
        }
    
    def _calculate_priority_score(self, goals: List[StrategicGoal]) -> float:
        """Calculate a score based on goal priorities."""
        if not goals:
            return 0.5
        
        priority_values = {
            ObjectivePriority.CRITICAL: 1.0,
            ObjectivePriority.HIGH: 0.8,
            ObjectivePriority.MEDIUM: 0.6,
            ObjectivePriority.LOW: 0.4,
        }
        
        avg_priority = sum(
            priority_values.get(g.priority, 0.5) for g in goals
        ) / len(goals)
        
        return avg_priority
    
    def _assess_resource_adequacy(self, strategy: Strategy) -> float:
        """Assess if resources are adequate for the strategy."""
        if not strategy.resource_allocation:
            return 0.5
        
        # Simple heuristic: higher resource allocation = higher adequacy
        total_resources = sum(strategy.resource_allocation.values())
        return min(1.0, total_resources / 10.0)
    
    def _assess_risk_factor(self, strategy: Strategy) -> float:
        """Assess the risk factor of a strategy."""
        if not strategy.risk_assessment:
            return 0.3
        
        # Average risk from assessment
        avg_risk = sum(strategy.risk_assessment.values()) / len(strategy.risk_assessment)
        return min(1.0, avg_risk)
    
    def list_strategies(self, status: Optional[StrategyStatus] = None) -> List[Strategy]:
        """List strategies, optionally filtered by status."""
        if status:
            return [s for s in self.strategies.values() if s.status == status]
        return list(self.strategies.values())
    
    def get_active_strategy(self) -> Optional[Strategy]:
        """Get the currently active strategy."""
        if self.active_strategy_id:
            return self.get_strategy(self.active_strategy_id)
        return None
    
    def generate_strategic_report(self, strategy_id: str) -> Dict[str, Any]:
        """Generate a comprehensive strategic report."""
        strategy = self.get_strategy(strategy_id)
        if strategy is None:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        assessment = self.assess_strategy(strategy_id)
        
        return {
            "strategy": strategy.to_dict(),
            "assessment": assessment,
            "recommendations": self._generate_recommendations(strategy),
            "next_steps": self._generate_next_steps(strategy),
        }
    
    def _generate_recommendations(self, strategy: Strategy) -> List[str]:
        """Generate recommendations for the strategy."""
        recommendations = []
        
        if strategy.success_probability < 0.5:
            recommendations.append("Consider revising goals to increase success probability")
        
        if not strategy.goals:
            recommendations.append("Add specific goals to make the strategy actionable")
        
        if not strategy.resource_allocation:
            recommendations.append("Allocate resources to support the strategy")
        
        if strategy.risk_assessment and max(strategy.risk_assessment.values()) > 0.7:
            recommendations.append("Develop mitigation plans for high-risk areas")
        
        return recommendations
    
    def _generate_next_steps(self, strategy: Strategy) -> List[str]:
        """Generate immediate next steps for the strategy."""
        steps = []
        
        if strategy.status == StrategyStatus.DRAFT:
            steps.append("Review and finalize strategy")
            steps.append("Allocate resources")
            steps.append("Activate strategy")
        elif strategy.status == StrategyStatus.ACTIVE:
            steps.append("Monitor progress on goals")
            steps.append("Adjust resource allocation as needed")
            steps.append("Update risk assessment regularly")
        
        return steps
