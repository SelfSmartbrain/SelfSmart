"""executive_agent.py

Autonomous executive agent for coordinating strategic decisions.
Acts as the central decision-making authority for the system.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger
from src.decision.decision_engine import DecisionEngine, DecisionContext, Decision
from src.decision.strategy_engine import StrategyEngine, Strategy
from src.decision.objective_engine import ObjectiveEngine, Objective

logger = get_logger(__name__)


class ExecutiveStatus(str, Enum):
    """Status of the executive agent."""
    IDLE = "idle"
    PLANNING = "planning"
    DECIDING = "deciding"
    EXECUTING = "executing"
    MONITORING = "monitoring"
    REVIEWING = "reviewing"


@dataclass
class ExecutiveAction:
    """An action taken by the executive agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: str = ""
    description: str = ""
    target: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action_type": self.action_type,
            "description": self.description,
            "target": self.target,
            "parameters": self.parameters,
            "timestamp": self.timestamp.isoformat(),
            "result": self.result,
            "metadata": self.metadata,
        }


class ExecutiveAgent:
    """Autonomous executive agent for strategic coordination."""
    
    def __init__(
        self,
        decision_engine: Optional[DecisionEngine] = None,
        strategy_engine: Optional[StrategyEngine] = None,
        objective_engine: Optional[ObjectiveEngine] = None,
    ):
        self.decision_engine = decision_engine or DecisionEngine()
        self.strategy_engine = strategy_engine or StrategyEngine()
        self.objective_engine = objective_engine or ObjectiveEngine()
        
        self.status = ExecutiveStatus.IDLE
        self.action_history: List[ExecutiveAction] = []
        self.current_strategy: Optional[Strategy] = None
        self.active_objectives: List[Objective] = []
        
        logger.info("ExecutiveAgent initialized")
    
    def plan_strategy(
        self,
        name: str,
        description: str,
        goals: List[Dict[str, Any]],
        time_horizon: str = "month",
    ) -> Strategy:
        """Plan a new strategy."""
        logger.info(f"Planning strategy: {name}")
        self.status = ExecutiveStatus.PLANNING
        
        from src.decision.strategy_engine import StrategicGoal, TimeHorizon
        
        strategic_goals = []
        for goal_data in goals:
            goal = StrategicGoal(
                description=goal_data.get("description", ""),
                horizon=TimeHorizon(time_horizon),
                estimated_effort=goal_data.get("effort", 10.0),
            )
            strategic_goals.append(goal)
        
        strategy = self.strategy_engine.create_strategy(
            name=name,
            description=description,
            time_horizon=TimeHorizon(time_horizon),
            goals=strategic_goals,
        )
        
        self.current_strategy = strategy
        self._record_action(
            action_type="plan_strategy",
            description=f"Planned strategy: {name}",
            target=strategy.id,
            parameters={"time_horizon": time_horizon},
        )
        
        self.status = ExecutiveStatus.IDLE
        return strategy
    
    def make_decision(
        self,
        query: str,
        context: Optional[DecisionContext] = None,
    ) -> Decision:
        """Make a strategic decision."""
        logger.info(f"Making decision: {query}")
        self.status = ExecutiveStatus.DECIDING
        
        if context is None:
            context = DecisionContext(
                objectives=[obj.name for obj in self.active_objectives],
            )
        
        decision = self.decision_engine.make_decision(query, context)
        
        self._record_action(
            action_type="make_decision",
            description=f"Made decision: {query}",
            target=decision.id,
            parameters={"selected_option": decision.selected_option_id},
        )
        
        self.status = ExecutiveStatus.IDLE
        return decision
    
    def execute_decision(self, decision_id: str) -> Dict[str, Any]:
        """Execute a decision."""
        logger.info(f"Executing decision: {decision_id}")
        self.status = ExecutiveStatus.EXECUTING
        
        result = self.decision_engine.execute_decision(decision_id)
        
        self._record_action(
            action_type="execute_decision",
            description=f"Executed decision: {decision_id}",
            target=decision_id,
            result=result,
        )
        
        self.status = ExecutiveStatus.IDLE
        return result
    
    def monitor_progress(self) -> Dict[str, Any]:
        """Monitor progress on current strategy and objectives."""
        logger.info("Monitoring progress")
        self.status = ExecutiveStatus.MONITORING
        
        progress = {
            "strategy": self.current_strategy.to_dict() if self.current_strategy else None,
            "objectives": [obj.to_dict() for obj in self.active_objectives],
            "decisions_made": len(self.decision_engine.list_decisions()),
            "action_count": len(self.action_history),
        }
        
        self._record_action(
            action_type="monitor_progress",
            description="Monitored system progress",
            result=progress,
        )
        
        self.status = ExecutiveStatus.IDLE
        return progress
    
    def review_performance(self) -> Dict[str, Any]:
        """Review performance and identify improvements."""
        logger.info("Reviewing performance")
        self.status = ExecutiveStatus.REVIEWING
        
        # Get decision statistics
        decision_stats = self.decision_engine.get_decision_statistics()
        
        # Get objective statistics
        objective_stats = self.objective_engine.get_objective_statistics()
        
        review = {
            "decision_stats": decision_stats,
            "objective_stats": objective_stats,
            "recommendations": self._generate_review_recommendations(
                decision_stats,
                objective_stats,
            ),
        }
        
        self._record_action(
            action_type="review_performance",
            description="Reviewed system performance",
            result=review,
        )
        
        self.status = ExecutiveStatus.IDLE
        return review
    
    def _generate_review_recommendations(
        self,
        decision_stats: Dict[str, Any],
        objective_stats: Dict[str, Any],
    ) -> List[str]:
        """Generate recommendations based on performance review."""
        recommendations = []
        
        # Check decision success rate
        total_decisions = decision_stats.get("total_decisions", 0)
        if total_decisions > 0:
            with_outcomes = decision_stats.get("decisions_with_outcomes", 0)
            if with_outcomes < total_decisions * 0.5:
                recommendations.append("Improve outcome tracking for decisions")
        
        # Check objective progress
        overdue = objective_stats.get("overdue_count", 0)
        if overdue > 0:
            recommendations.append(f"Address {overdue} overdue objectives")
        
        # Check average confidence
        avg_confidence = decision_stats.get("average_confidence", 0.0)
        if avg_confidence < 0.6:
            recommendations.append("Improve decision confidence through better information")
        
        if not recommendations:
            recommendations.append("Performance is satisfactory, continue current approach")
        
        return recommendations
    
    def add_objective(
        self,
        name: str,
        description: str,
        priority: str = "medium",
        target_value: float = 1.0,
    ) -> Objective:
        """Add an objective for the executive to pursue."""
        from src.decision.objective_engine import ObjectivePriority
        
        objective = self.objective_engine.create_objective(
            name=name,
            description=description,
            priority=ObjectivePriority(priority),
            target_value=target_value,
        )
        
        self.active_objectives.append(objective)
        
        self._record_action(
            action_type="add_objective",
            description=f"Added objective: {name}",
            target=objective.id,
        )
        
        return objective
    
    def update_objective_progress(self, objective_id: str, progress: float) -> None:
        """Update progress on an objective."""
        self.objective_engine.update_progress(objective_id, progress)
        
        self._record_action(
            action_type="update_objective",
            description=f"Updated objective progress: {objective_id}",
            target=objective_id,
            parameters={"progress": progress},
        )
    
    def _record_action(
        self,
        action_type: str,
        description: str,
        target: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an action taken by the executive."""
        action = ExecutiveAction(
            action_type=action_type,
            description=description,
            target=target,
            parameters=parameters or {},
            result=result,
        )
        self.action_history.append(action)
    
    def get_action_history(self, limit: int = 10) -> List[ExecutiveAction]:
        """Get recent action history."""
        return self.action_history[-limit:]
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the executive agent."""
        return {
            "status": self.status.value,
            "current_strategy": self.current_strategy.name if self.current_strategy else None,
            "active_objectives": len(self.active_objectives),
            "total_actions": len(self.action_history),
            "last_action": self.action_history[-1].to_dict() if self.action_history else None,
        }
