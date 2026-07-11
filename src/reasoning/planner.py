"""
Planner - Goal-oriented planning and execution

The Planner is responsible for:
- Creating plans to achieve goals
- Decomposing goals into sub-goals
- Scheduling plan execution
- Monitoring plan progress
- Adapting plans to changing conditions
- Dynamic re-planning on environmental drift
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)

# Optional imports for drift detection (avoid circular imports)
try:
    from src.reasoning.drift_detector import EnvironmentalDriftDetector, DriftSignal
    from src.reasoning.reactive_replanner import ReactiveRePlanner, ReplanContext, ReplanStrategy, ReplanningCoordinator
    DRIFT_DETECTION_AVAILABLE = True
except ImportError:
    DRIFT_DETECTION_AVAILABLE = False


class PlanStatus(Enum):
    """Status of a plan"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


@dataclass
class Action:
    """An action in a plan"""
    action_id: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: float = 10.0
    priority: int = 5


@dataclass
class Plan:
    """A plan to achieve a goal"""
    plan_id: str
    goal: str
    actions: List[Action]
    status: PlanStatus = PlanStatus.PENDING
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[float]:
        """Get plan duration if completed"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None


class Planner:
    """
    Goal-oriented planner.
    
    Creates and executes plans to achieve goals by:
    - Decomposing goals into actionable steps
    - Managing dependencies between actions
    - Scheduling action execution
    - Monitoring progress and adapting
    - Dynamic re-planning on environmental drift
    """
    
    def __init__(self, llm_client: Any = None, memory_fabric: Any = None):
        self._plans: Dict[str, Plan] = {}
        self._active_plans: Set[str] = set()
        self._llm = llm_client
        self._memory = memory_fabric
        
        # Planning strategies
        self._strategies = {
            "hierarchical": self._hierarchical_planning,
            "forward": self._forward_planning,
            "backward": self._backward_planning,
        }
        
        # Drift detection and re-planning
        self._drift_detector: Optional[EnvironmentalDriftDetector] = None
        self._replanner: Optional[ReactiveRePlanner] = None
        self._replanning_coordinator: Optional[ReplanningCoordinator] = None
        self._drift_monitoring_enabled = False
        
        # Statistics
        self._plans_created = 0
        self._plans_completed = 0
        self._plans_failed = 0
        self._replans_triggered = 0
    
    async def initialize(self, enable_drift_detection: bool = True) -> None:
        """Initialize the planner with optional drift detection"""
        logger.info("Planner initialized")
        
        if enable_drift_detection and DRIFT_DETECTION_AVAILABLE and self._llm:
            await self._initialize_drift_detection()
    
    async def _initialize_drift_detection(self) -> None:
        """Initialize drift detection and re-planning components"""
        try:
            self._drift_detector = EnvironmentalDriftDetector(
                memory_fabric=self._memory,
                llm_client=self._llm,
                drift_threshold=0.3,
                check_interval=30,
            )
            await self._drift_detector.initialize()
            
            self._replanner = ReactiveRePlanner(
                planner=self,
                llm_client=self._llm,
                memory_fabric=self._memory,
            )
            await self._replanner.initialize()
            
            self._replanning_coordinator = ReplanningCoordinator(
                drift_detector=self._drift_detector,
                replanner=self._replanner,
                planner=self,
            )
            
            self._drift_monitoring_enabled = True
            logger.info("Drift detection and re-planning enabled")
        except Exception as e:
            logger.warning(f"Failed to initialize drift detection: {e}")
            self._drift_monitoring_enabled = False
    
    async def create_plan(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        strategy: str = "hierarchical",
    ) -> Plan:
        """
        Create a plan to achieve a goal.
        
        Args:
            goal: Goal to achieve
            context: Additional context
            strategy: Planning strategy to use
            
        Returns:
            Created plan
        """
        plan_id = f"plan_{datetime.now().timestamp()}"
        
        # Select planning strategy
        planning_func = self._strategies.get(strategy, self._hierarchical_planning)
        
        # Generate actions
        actions = await planning_func(goal, context or {})
        
        # Create plan
        plan = Plan(
            plan_id=plan_id,
            goal=goal,
            actions=actions,
            metadata={"strategy": strategy, "context": context},
        )
        
        self._plans[plan_id] = plan
        self._plans_created += 1
        
        logger.info(f"Created plan {plan_id} with {len(actions)} actions")
        return plan
    
    async def _hierarchical_planning(
        self,
        goal: str,
        context: Dict[str, Any],
    ) -> List[Action]:
        """
        Hierarchical planning: decompose goal into sub-goals recursively.
        
        This is the default strategy and works well for complex goals.
        """
        actions = []
        
        # Placeholder for hierarchical decomposition
        # In full implementation, would use recursive goal decomposition
        
        # Simple example: create a few placeholder actions
        actions.append(Action(
            action_id=f"action_{len(actions)}",
            description=f"Analyze goal: {goal}",
            priority=10,
        ))
        
        actions.append(Action(
            action_id=f"action_{len(actions)}",
            description=f"Identify resources for: {goal}",
            priority=8,
            dependencies=[actions[0].action_id],
        ))
        
        actions.append(Action(
            action_id=f"action_{len(actions)}",
            description=f"Execute plan for: {goal}",
            priority=9,
            dependencies=[actions[1].action_id],
        ))
        
        return actions
    
    async def _forward_planning(
        self,
        goal: str,
        context: Dict[str, Any],
    ) -> List[Action]:
        """
        Forward planning: start from current state and move toward goal.
        """
        actions = []
        
        # Placeholder for forward planning
        # In full implementation, would use state-space search
        
        actions.append(Action(
            action_id=f"action_{len(actions)}",
            description=f"Assess current state for: {goal}",
            priority=10,
        ))
        
        actions.append(Action(
            action_id=f"action_{len(actions)}",
            description=f"Identify next steps toward: {goal}",
            priority=8,
            dependencies=[actions[0].action_id],
        ))
        
        return actions
    
    async def _backward_planning(
        self,
        goal: str,
        context: Dict[str, Any],
    ) -> List[Action]:
        """
        Backward planning: start from goal and work backward to current state.
        """
        actions = []
        
        # Placeholder for backward planning
        # In full implementation, would use goal regression
        
        actions.append(Action(
            action_id=f"action_{len(actions)}",
            description=f"Define final state for: {goal}",
            priority=10,
        ))
        
        actions.append(Action(
            action_id=f"action_{len(actions)}",
            description=f"Identify prerequisites for: {goal}",
            priority=9,
            dependencies=[actions[0].action_id],
        ))
        
        actions.append(Action(
            action_id=f"action_{len(actions)}",
            description=f"Plan from current state to prerequisites",
            priority=8,
            dependencies=[actions[1].action_id],
        ))
        
        return actions
    
    async def execute_plan(
        self,
        plan_id: str,
        get_state_func: Optional[Callable] = None,
        get_context_func: Optional[Callable] = None,
    ) -> bool:
        """
        Execute a plan with optional drift monitoring.
        
        Args:
            plan_id: Plan identifier
            get_state_func: Function to get current execution state (for drift detection)
            get_context_func: Function to get current context (for drift detection)
            
        Returns:
            True if plan completed successfully
        """
        if plan_id not in self._plans:
            logger.error(f"Plan {plan_id} not found")
            return False
        
        plan = self._plans[plan_id]
        plan.status = PlanStatus.IN_PROGRESS
        plan.started_at = datetime.now().timestamp()
        self._active_plans.add(plan_id)
        
        # Start drift monitoring if enabled and functions provided
        if self._drift_monitoring_enabled and get_state_func and get_context_func:
            await self._start_drift_monitoring(plan_id, get_state_func, get_context_func)
        
        try:
            # Execute actions in dependency order
            executed_actions = set()
            
            while len(executed_actions) < len(plan.actions):
                # Check for drift before each action batch
                if self._drift_monitoring_enabled:
                    drift_result = await self._check_and_handle_drift(plan_id, len(executed_actions))
                    if drift_result and drift_result.get("replanned"):
                        # Plan was re-planned, refresh reference
                        plan = self._plans.get(plan_id)
                        if not plan:
                            logger.error(f"Plan {plan_id} lost after re-plan")
                            return False
                
                # Find actions whose dependencies are satisfied
                ready_actions = [
                    action for action in plan.actions
                    if action.action_id not in executed_actions
                    and all(dep in executed_actions for dep in action.dependencies)
                ]
                
                if not ready_actions:
                    logger.error(f"Plan {plan_id} has circular dependencies")
                    plan.status = PlanStatus.FAILED
                    self._plans_failed += 1
                    return False
                
                # Execute ready actions (could be parallelized)
                for action in ready_actions:
                    success = await self._execute_action(action)
                    
                    if not success:
                        logger.error(f"Action {action.action_id} failed")
                        plan.status = PlanStatus.FAILED
                        self._plans_failed += 1
                        return False
                    
                    executed_actions.add(action.action_id)
            
            # Plan completed successfully
            plan.status = PlanStatus.COMPLETED
            plan.completed_at = datetime.now().timestamp()
            self._active_plans.discard(plan_id)
            self._plans_completed += 1
            
            # Stop drift monitoring
            if self._drift_monitoring_enabled:
                await self._stop_drift_monitoring(plan_id)
            
            logger.info(f"Plan {plan_id} completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error executing plan {plan_id}: {e}")
            plan.status = PlanStatus.FAILED
            self._plans_failed += 1
            
            if self._drift_monitoring_enabled:
                await self._stop_drift_monitoring(plan_id)
            
            return False
    
    async def _start_drift_monitoring(
        self,
        plan_id: str,
        get_state_func: Callable,
        get_context_func: Callable,
    ) -> None:
        """Start drift monitoring for a plan"""
        # Extract expected states from plan
        expected_states = []
        for action in self._plans[plan_id].actions:
            expected_states.append({
                "action": action.action_id,
                "description": action.description,
                "expected_outcome": f"Completed: {action.description}",
            })
        
        # Get baseline state
        baseline_state = await get_state_func() if callable(get_state_func) else {}
        
        await self._drift_detector.register_plan(plan_id, expected_states, baseline_state)
        await self._drift_detector.start_monitoring(plan_id, get_state_func, get_context_func)
        
        # Set up re-plan callback
        async def on_replan(new_plan_id: str, result: Any):
            self._replans_triggered += 1
            logger.info(f"Plan {plan_id} re-planned to {new_plan_id}: {result.changes_summary}")
        
        await self._replanning_coordinator.start_monitoring_plan(
            plan_id, get_state_func, get_context_func, on_replan
        )
    
    async def _check_and_handle_drift(
        self,
        plan_id: str,
        current_step: int,
    ) -> Optional[Dict[str, Any]]:
        """Check for drift and handle if detected"""
        if not self._replanning_coordinator:
            return None
        
        get_state_func = self._drift_detector._get_state_funcs.get(plan_id)
        get_context_func = self._drift_detector._get_context_funcs.get(plan_id)
        
        if not get_state_func or not get_context_func:
            return None
        
        current_state = await get_state_func() if callable(get_state_func) else {}
        context = await get_context_func() if callable(get_context_func) else {}
        context["goal"] = self._plans[plan_id].goal
        context["completed_actions"] = [a.action_id for a in self._plans[plan_id].actions if a.action_id in current_state.get("executed", set())]
        context["remaining_actions"] = [a for a in self._plans[plan_id].actions if a.action_id not in current_state.get("executed", set())]
        
        result = await self._replanning_coordinator.check_and_replan(plan_id, current_step, current_state, context)
        
        if result:
            return {"replanned": True, "result": result}
        return {"replanned": False}
    
    async def _stop_drift_monitoring(self, plan_id: str) -> None:
        """Stop drift monitoring for a plan"""
        if self._drift_detector:
            await self._drift_detector.stop_monitoring(plan_id)
        if self._replanning_coordinator:
            await self._replanning_coordinator.stop_monitoring_plan(plan_id)
    
    async def _execute_action(self, action: Action) -> bool:
        """
        Execute a single action.
        
        Args:
            action: Action to execute
            
        Returns:
            True if action executed successfully
        """
        # Placeholder for action execution
        # In full implementation, would delegate to appropriate executor
        logger.debug(f"Executing action {action.action_id}: {action.description}")
        
        # Simulate execution time
        await asyncio.sleep(min(1.0, action.estimated_duration / 10.0))
        
        return True
    
    async def adapt_plan(
        self,
        plan_id: str,
        new_context: Dict[str, Any],
    ) -> bool:
        """
        Adapt a plan to changing conditions.
        
        Args:
            plan_id: Plan identifier
            new_context: New context information
            
        Returns:
            True if plan adapted successfully
        """
        if plan_id not in self._plans:
            logger.error(f"Plan {plan_id} not found")
            return False
        
        plan = self._plans[plan_id]
        
        # Placeholder for plan adaptation
        # In full implementation, would re-plan with new
        
        logger.info(f"Adapting plan {plan_id} to new context")
        return True
    
    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Get a plan by ID"""
        return self._plans.get(plan_id)
    
    def get_active_plans(self) -> List[Plan]:
        """Get all active plans"""
        return [self._plans[pid] for pid in self._active_plans]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get planner metrics"""
        metrics = {
            "plans_created": self._plans_created,
            "plans_completed": self._plans_completed,
            "plans_failed": self._plans_failed,
            "active_plans": len(self._active_plans),
            "success_rate": (
                self._plans_completed / self._plans_created
                if self._plans_created > 0 else 0.0
            ),
            "replans_triggered": self._replans_triggered,
            "drift_detection_enabled": self._drift_monitoring_enabled,
        }
        
        if self._drift_detector:
            metrics["drift_signals_detected"] = len(self._drift_detector.get_drift_history())
        
        if self._replanner:
            metrics["replan_history"] = len(self._replanner.get_replan_history())
        
        return metrics
