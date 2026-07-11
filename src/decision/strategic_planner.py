"""strategic_planner.py

Strategic planner for creating detailed plans across time horizons.
Breaks down high-level strategies into actionable plans.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger
from src.decision.strategy_engine import Strategy, StrategicGoal, TimeHorizon

logger = get_logger(__name__)


class PlanStatus(str, Enum):
    """Status of a plan."""
    DRAFT = "draft"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class ActionItem:
    """An actionable item in a plan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    assigned_to: Optional[str] = None
    estimated_duration: float = 1.0  # in hours
    dependencies: List[str] = field(default_factory=list)
    priority: int = 5  # 1-10
    status: str = "pending"
    due_date: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "assigned_to": self.assigned_to,
            "estimated_duration": self.estimated_duration,
            "dependencies": self.dependencies,
            "priority": self.priority,
            "status": self.status,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "metadata": self.metadata,
        }


@dataclass
class Plan:
    """A detailed plan for achieving strategic goals."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    strategy_id: Optional[str] = None
    goal_id: Optional[str] = None
    time_horizon: TimeHorizon = TimeHorizon.MONTH
    status: PlanStatus = PlanStatus.DRAFT
    action_items: List[ActionItem] = field(default_factory=list)
    timeline: Dict[str, Any] = field(default_factory=dict)
    resource_requirements: Dict[str, float] = field(default_factory=dict)
    milestones: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "strategy_id": self.strategy_id,
            "goal_id": self.goal_id,
            "time_horizon": self.time_horizon.value,
            "status": self.status.value,
            "action_items": [a.to_dict() for a in self.action_items],
            "timeline": self.timeline,
            "resource_requirements": self.resource_requirements,
            "milestones": self.milestones,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


class StrategicPlanner:
    """Creates detailed strategic plans from high-level strategies."""
    
    def __init__(self):
        self.plans: Dict[str, Plan] = {}
        logger.info("StrategicPlanner initialized")
    
    def create_plan(
        self,
        name: str,
        description: str,
        strategy_id: Optional[str] = None,
        goal_id: Optional[str] = None,
        time_horizon: TimeHorizon = TimeHorizon.MONTH,
    ) -> Plan:
        """Create a new plan."""
        plan = Plan(
            name=name,
            description=description,
            strategy_id=strategy_id,
            goal_id=goal_id,
            time_horizon=time_horizon,
        )
        
        self.plans[plan.id] = plan
        logger.info(f"Created plan: {name}")
        return plan
    
    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Get a plan by ID."""
        return self.plans.get(plan_id)
    
    def update_plan(self, plan_id: str, updates: Dict[str, Any]) -> Optional[Plan]:
        """Update a plan."""
        plan = self.get_plan(plan_id)
        if plan is None:
            return None
        
        for key, value in updates.items():
            if hasattr(plan, key):
                setattr(plan, key, value)
        
        plan.updated_at = datetime.now(timezone.utc)
        logger.info(f"Updated plan: {plan_id}")
        return plan
    
    def add_action_item(self, plan_id: str, action: ActionItem) -> None:
        """Add an action item to a plan."""
        plan = self.get_plan(plan_id)
        if plan:
            plan.action_items.append(action)
            logger.info(f"Added action item to plan: {plan_id}")
    
    def remove_action_item(self, plan_id: str, action_id: str) -> None:
        """Remove an action item from a plan."""
        plan = self.get_plan(plan_id)
        if plan:
            plan.action_items = [a for a in plan.action_items if a.id != action_id]
            logger.info(f"Removed action item from plan: {plan_id}")
    
    def generate_plan_from_strategy(
        self,
        strategy_id: str,
        strategy: Strategy,
    ) -> Plan:
        """Generate a detailed plan from a strategy."""
        plan = self.create_plan(
            name=f"Plan for {strategy.name}",
            description=f"Detailed plan to execute strategy: {strategy.description}",
            strategy_id=strategy_id,
            time_horizon=strategy.time_horizon,
        )
        
        # Generate action items from goals
        for goal in strategy.goals:
            actions = self._generate_actions_from_goal(goal)
            plan.action_items.extend(actions)
        
        # Set timeline based on time horizon
        plan.timeline = self._generate_timeline(strategy.time_horizon)
        
        # Estimate resource requirements
        plan.resource_requirements = self._estimate_resources(plan.action_items)
        
        # Define milestones
        plan.milestones = self._define_milestones(plan.action_items, strategy.time_horizon)
        
        plan.status = PlanStatus.APPROVED
        plan.updated_at = datetime.now(timezone.utc)
        
        logger.info(f"Generated plan from strategy: {strategy_id}")
        return plan
    
    def _generate_actions_from_goal(self, goal: StrategicGoal) -> List[ActionItem]:
        """Generate action items from a strategic goal."""
        actions = []
        
        # Break down goal into actions
        action_count = max(3, int(goal.estimated_effort))
        for i in range(action_count):
            action = ActionItem(
                description=f"Step {i + 1} toward: {goal.description}",
                estimated_duration=goal.estimated_effort / action_count,
                priority=8 if goal.priority.value in ["critical", "high"] else 5,
                due_date=goal.deadline,
            )
            actions.append(action)
        
        return actions
    
    def _generate_timeline(self, horizon: TimeHorizon) -> Dict[str, Any]:
        """Generate a timeline based on time horizon."""
        now = datetime.now(timezone.utc)
        
        horizon_durations = {
            TimeHorizon.HOUR: timedelta(hours=1),
            TimeHorizon.DAY: timedelta(days=1),
            TimeHorizon.WEEK: timedelta(weeks=1),
            TimeHorizon.MONTH: timedelta(days=30),
            TimeHorizon.YEAR: timedelta(days=365),
        }
        
        duration = horizon_durations.get(horizon, timedelta(days=30))
        
        return {
            "start_date": now.isoformat(),
            "end_date": (now + duration).isoformat(),
            "duration_days": duration.days,
            "phases": self._generate_phases(horizon),
        }
    
    def _generate_phases(self, horizon: TimeHorizon) -> List[Dict[str, Any]]:
        """Generate phases for the timeline."""
        phases = []
        
        if horizon == TimeHorizon.MONTH:
            phases = [
                {"name": "Preparation", "duration_days": 5},
                {"name": "Execution", "duration_days": 20},
                {"name": "Review", "duration_days": 5},
            ]
        elif horizon == TimeHorizon.WEEK:
            phases = [
                {"name": "Planning", "duration_days": 1},
                {"name": "Execution", "duration_days": 5},
                {"name": "Review", "duration_days": 1},
            ]
        else:
            phases = [
                {"name": "Planning", "duration_days": 1},
                {"name": "Execution", "duration_days": 3},
            ]
        
        return phases
    
    def _estimate_resources(self, actions: List[ActionItem]) -> Dict[str, float]:
        """Estimate resource requirements for action items."""
        total_hours = sum(a.estimated_duration for a in actions)
        
        return {
            "time_hours": total_hours,
            "compute_units": total_hours * 0.5,
            "financial_cost": total_hours * 50.0,  # $50 per hour
        }
    
    def _define_milestones(
        self,
        actions: List[ActionItem],
        horizon: TimeHorizon,
    ) -> List[str]:
        """Define milestones for the plan."""
        milestones = []
        
        if not actions:
            return milestones
        
        # Milestone at 25%, 50%, 75%, 100%
        total_actions = len(actions)
        milestones = [
            f"Complete {int(total_actions * 0.25)} actions",
            f"Complete {int(total_actions * 0.5)} actions",
            f"Complete {int(total_actions * 0.75)} actions",
            f"Complete all {total_actions} actions",
        ]
        
        return milestones
    
    def approve_plan(self, plan_id: str) -> None:
        """Approve a plan for execution."""
        plan = self.get_plan(plan_id)
        if plan:
            plan.status = PlanStatus.APPROVED
            logger.info(f"Approved plan: {plan_id}")
    
    def start_plan(self, plan_id: str) -> None:
        """Start executing a plan."""
        plan = self.get_plan(plan_id)
        if plan:
            plan.status = PlanStatus.IN_PROGRESS
            logger.info(f"Started plan: {plan_id}")
    
    def complete_plan(self, plan_id: str) -> None:
        """Mark a plan as completed."""
        plan = self.get_plan(plan_id)
        if plan:
            plan.status = PlanStatus.COMPLETED
            logger.info(f"Completed plan: {plan_id}")
    
    def list_plans(self, status: Optional[PlanStatus] = None) -> List[Plan]:
        """List plans, optionally filtered by status."""
        if status:
            return [p for p in self.plans.values() if p.status == status]
        return list(self.plans.values())
    
    def get_plan_progress(self, plan_id: str) -> Dict[str, Any]:
        """Get progress information for a plan."""
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"Plan {plan_id} not found")
        
        if not plan.action_items:
            return {"progress": 0.0, "completed_actions": 0, "total_actions": 0}
        
        completed = sum(1 for a in plan.action_items if a.status == "completed")
        progress = completed / len(plan.action_items)
        
        return {
            "progress": progress,
            "completed_actions": completed,
            "total_actions": len(plan.action_items),
            "pending_actions": len(plan.action_items) - completed,
        }
