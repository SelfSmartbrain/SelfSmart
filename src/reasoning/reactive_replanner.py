"""
Reactive Re-Planner - Dynamic Re-Planning

Generates corrective plans when drift is detected, enabling
adaptive execution in changing environments.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class ReplanStrategy(Enum):
    """Re-planning strategies"""
    INCREMENTAL = "incremental"      # Adjust remaining steps
    FROM_CURRENT = "from_current"    # Re-plan from current state
    FULL_REPLAN = "full_replan"      # Complete re-plan
    GOAL_ADJUST = "goal_adjust"      # Adjust goal then re-plan


@dataclass
class ReplanContext:
    """Context for re-planning"""
    plan_id: str
    current_step: int
    current_state: Dict[str, Any]
    drift_signals: List[Any]
    original_goal: str
    completed_actions: List[str]
    remaining_actions: List[Dict[str, Any]]
    resources: Dict[str, Any]
    constraints: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReplanResult:
    """Result of re-planning"""
    success: bool
    new_plan_id: Optional[str] = None
    strategy_used: Optional[ReplanStrategy] = None
    changes_summary: str = ""
    affected_actions: List[str] = field(default_factory=list)
    error: Optional[str] = None


class ReactiveRePlanner:
    """
    Generates corrective plans when environmental drift is detected.
    
    Strategies:
    - Incremental: Modify only affected remaining actions
    - From Current: Re-plan from current state to goal
    - Full Replan: Complete re-plan with new goal understanding
    - Goal Adjust: Modify goal based on drift, then re-plan
    """

    def __init__(
        self,
        planner: Any,
        llm_client: Any,
        memory_fabric: Any = None,
        default_strategy: ReplanStrategy = ReplanStrategy.FROM_CURRENT,
    ):
        self.planner = planner
        self.llm = llm_client
        self.memory = memory_fabric
        self.default_strategy = default_strategy

        self._replan_history: List[Dict[str, Any]] = []

    async def initialize(self) -> None:
        """Initialize reactive re-planner"""
        logger.info("ReactiveRePlanner initialized")

    async def maybe_replan(
        self,
        context: ReplanContext,
        strategy: Optional[ReplanStrategy] = None,
    ) -> ReplanResult:
        """
        Determine if re-planning needed and execute.
        
        Args:
            context: Re-planning context with drift info
            strategy: Override default strategy
            
        Returns:
            ReplanResult with new plan or error
        """
        strategy = strategy or self.default_strategy
        
        # Check if any drift signals warrant re-planning
        if not self._should_replan(context.drift_signals):
            return ReplanResult(
                success=True,
                changes_summary="No significant drift requiring re-plan",
            )
        
        logger.info(f"Re-planning for plan {context.plan_id} using {strategy.value} strategy")
        
        try:
            if strategy == ReplanStrategy.INCREMENTAL:
                result = await self._incremental_replan(context)
            elif strategy == ReplanStrategy.FROM_CURRENT:
                result = await self._replan_from_current(context)
            elif strategy == ReplanStrategy.FULL_REPLAN:
                result = await self._full_replan(context)
            elif strategy == ReplanStrategy.GOAL_ADJUST:
                result = await self._goal_adjust_replan(context)
            else:
                result = await self._replan_from_current(context)
            
            # Record re-plan
            self._record_replan(context.plan_id, strategy, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Re-planning failed: {e}")
            return ReplanResult(
                success=False,
                error=str(e),
            )

    def _should_replan(self, drift_signals: List[Any]) -> bool:
        """Determine if drift signals warrant re-planning"""
        if not drift_signals:
            return False
        
        # Re-plan if any high-severity signal
        for signal in drift_signals:
            severity = getattr(signal, 'severity', 0)
            if severity >= 0.5:
                return True
        
        # Or multiple medium signals
        medium_count = sum(1 for s in drift_signals if getattr(s, 'severity', 0) >= 0.3)
        return medium_count >= 2

    async def _incremental_replan(self, context: ReplanContext) -> ReplanResult:
        """Modify only affected remaining actions"""
        # Identify affected actions from drift signals
        affected = set()
        for signal in context.drift_signals:
            affected.update(getattr(signal, 'affected_actions', []))
        
        # Filter remaining actions to only affected ones
        new_remaining = []
        for action in context.remaining_actions:
            if action.get("action_id") in affected:
                # Regenerate this action with current state
                new_action = await self._regenerate_action(action, context)
                new_remaining.append(new_action)
            else:
                new_remaining.append(action)
        
        # Create updated plan
        new_plan = await self._create_updated_plan(
            context,
            new_remaining,
            "Incremental adjustment of affected actions",
        )
        
        return ReplanResult(
            success=True,
            new_plan_id=new_plan.plan_id if new_plan else None,
            strategy_used=ReplanStrategy.INCREMENTAL,
            changes_summary=f"Adjusted {len(affected)} affected actions",
            affected_actions=list(affected),
        )

    async def _replan_from_current(self, context: ReplanContext) -> ReplanResult:
        """Re-plan from current state to original goal"""
        # Create new goal context with current state
        replan_context = {
            **context.metadata,
            "current_state": context.current_state,
            "completed_actions": context.completed_actions,
            "resources": context.resources,
            "constraints": context.constraints,
            "replan_reason": "Environmental drift detected",
        }
        
        # Generate new plan from current state
        new_plan = await self.planner.create_plan(
            goal=context.original_goal,
            context=replan_context,
            strategy="hierarchical",
        )
        
        if not new_plan:
            return ReplanResult(
                success=False,
                error="Planner failed to generate new plan",
            )
        
        return ReplanResult(
            success=True,
            new_plan_id=new_plan.plan_id,
            strategy_used=ReplanStrategy.FROM_CURRENT,
            changes_summary=f"Full re-plan from current state (step {context.current_step})",
            affected_actions=[a.action_id for a in new_plan.actions],
        )

    async def _full_replan(self, context: ReplanContext) -> ReplanResult:
        """Complete re-plan with drift-informed context"""
        # Use LLM to analyze drift and adjust planning approach
        drift_summary = self._summarize_drift(context.drift_signals)
        
        enhanced_context = {
            **context.metadata,
            "current_state": context.current_state,
            "completed_actions": context.completed_actions,
            "resources": context.resources,
            "constraints": context.constraints,
            "drift_analysis": drift_summary,
            "lessons_learned": await self._extract_lessons(context),
            "replan_reason": "Significant environmental drift requiring full re-plan",
        }
        
        new_plan = await self.planner.create_plan(
            goal=context.original_goal,
            context=enhanced_context,
            strategy="hierarchical",
        )
        
        if not new_plan:
            return ReplanResult(
                success=False,
                error="Planner failed to generate new plan",
            )
        
        return ReplanResult(
            success=True,
            new_plan_id=new_plan.plan_id,
            strategy_used=ReplanStrategy.FULL_REPLAN,
            changes_summary=f"Full re-plan with drift analysis: {drift_summary[:100]}...",
            affected_actions=[a.action_id for a in new_plan.actions],
        )

    async def _goal_adjust_replan(self, context: ReplanContext) -> ReplanResult:
        """Adjust goal based on drift, then re-plan"""
        # Use LLM to determine adjusted goal
        drift_summary = self._summarize_drift(context.drift_signals)
        
        prompt = f"""The original goal may need adjustment due to environmental drift.

Original Goal: {context.original_goal}
Current State: {context.current_state}
Drift Detected: {drift_summary}
Completed Actions: {context.completed_actions}
Resources: {context.resources}
Constraints: {context.constraints}

Provide an adjusted goal that is achievable given the current situation.
If the goal is still achievable, respond with the original goal.
If partially achievable, provide a modified scope.
If obsolete, provide a new relevant goal.

Adjusted Goal:"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            adjusted_goal = response.content if hasattr(response, 'content') else str(response)
            adjusted_goal = adjusted_goal.strip()
        except Exception as e:
            logger.error(f"Goal adjustment failed: {e}")
            adjusted_goal = context.original_goal
        
        if adjusted_goal == context.original_goal:
            # No adjustment needed, fall back to from_current
            return await self._replan_from_current(context)
        
        # Re-plan with adjusted goal
        enhanced_context = {
            **context.metadata,
            "current_state": context.current_state,
            "completed_actions": context.completed_actions,
            "resources": context.resources,
            "constraints": context.constraints,
            "original_goal": context.original_goal,
            "goal_adjustment_reason": drift_summary,
        }
        
        new_plan = await self.planner.create_plan(
            goal=adjusted_goal,
            context=enhanced_context,
            strategy="hierarchical",
        )
        
        if not new_plan:
            return ReplanResult(
                success=False,
                error="Planner failed to generate plan for adjusted goal",
            )
        
        return ReplanResult(
            success=True,
            new_plan_id=new_plan.plan_id,
            strategy_used=ReplanStrategy.GOAL_ADJUST,
            changes_summary=f"Goal adjusted: '{context.original_goal}' -> '{adjusted_goal}'",
            affected_actions=[a.action_id for a in new_plan.actions],
        )

    async def _regenerate_action(
        self,
        action: Dict[str, Any],
        context: ReplanContext,
    ) -> Dict[str, Any]:
        """Regenerate a single action with current context"""
        # Use LLM to adapt action to current state
        prompt = f"""Adapt this action to the current state.

Original Action: {action}
Current State: {context.current_state}
Resources: {context.resources}
Constraints: {context.constraints}

Provide updated action parameters:"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            adapted = response.content if hasattr(response, 'content') else str(response)
            # Parse adapted action (simplified)
            return {**action, "adapted": True, "adaptation_note": adapted}
        except Exception:
            return action

    async def _create_updated_plan(
        self,
        context: ReplanContext,
        remaining_actions: List[Dict[str, Any]],
        summary: str,
    ) -> Optional[Any]:
        """Create a new plan with updated actions"""
        # This would integrate with the planner's internal plan structure
        # For now, create via planner with context
        return await self.planner.create_plan(
            goal=context.original_goal,
            context={
                **context.metadata,
                "predefined_actions": remaining_actions,
                "current_step": context.current_step,
            },
        )

    def _summarize_drift(self, drift_signals: List[Any]) -> str:
        """Summarize drift signals for context"""
        if not drift_signals:
            return "No drift signals"
        
        summaries = []
        for signal in drift_signals:
            dtype = getattr(signal, 'drift_type', 'unknown')
            desc = getattr(signal, 'description', '')
            severity = getattr(signal, 'severity', 0)
            summaries.append(f"[{dtype.value} sev={severity:.2f}] {desc}")
        
        return "; ".join(summaries)

    async def _extract_lessons(self, context: ReplanContext) -> List[str]:
        """Extract lessons from drift for future planning"""
        lessons = []
        
        for signal in context.drift_signals:
            dtype = getattr(signal, 'drift_type', None)
            if dtype:
                lessons.append(f"Monitor for {dtype.value} in similar contexts")
        
        # Add resource lessons
        if context.resources:
            for resource, amount in context.resources.items():
                if amount < 10:  # Arbitrary low threshold
                    lessons.append(f"Resource {resource} tends to deplete faster than expected")
        
        return lessons

    def _record_replan(
        self,
        original_plan_id: str,
        strategy: ReplanStrategy,
        result: ReplanResult,
    ) -> None:
        """Record re-plan in history"""
        self._replan_history.append({
            "original_plan_id": original_plan_id,
            "new_plan_id": result.new_plan_id,
            "strategy": strategy.value,
            "success": result.success,
            "changes_summary": result.changes_summary,
            "timestamp": datetime.now().timestamp(),
            "error": result.error,
        })

    def get_replan_history(self, plan_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get re-planning history"""
        if plan_id:
            return [r for r in self._replan_history if r["original_plan_id"] == plan_id]
        return self._replan_history


class ReplanningCoordinator:
    """
    Coordinates drift detection and re-planning in the execution loop.
    """

    def __init__(
        self,
        drift_detector: Any,
        replanner: ReactiveRePlanner,
        planner: Any,
    ):
        self.drift_detector = drift_detector
        self.replanner = replanner
        self.planner = planner

        self._active_monitors: Dict[str, Dict[str, Any]] = {}

    async def start_monitoring_plan(
        self,
        plan_id: str,
        get_state_func: callable,
        get_context_func: callable,
        on_replan: callable,
    ) -> None:
        """Start integrated drift monitoring with auto-replan"""
        # Register with drift detector
        await self.drift_detector.start_monitoring(plan_id, get_state_func, get_context_func)
        
        # Store callback
        self._active_monitors[plan_id] = {
            "on_replan": on_replan,
            "last_check": 0,
        }

    async def check_and_replan(
        self,
        plan_id: str,
        current_step: int,
        current_state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Optional[Any]:
        """Check for drift and re-plan if needed"""
        # Check drift
        signals = await self.drift_detector.check_drift(plan_id, current_step, current_state, context)
        
        if not signals:
            return None
        
        # Build replan context
        replan_context = ReplanContext(
            plan_id=plan_id,
            current_step=current_step,
            current_state=current_state,
            drift_signals=signals,
            original_goal=context.get("goal", ""),
            completed_actions=context.get("completed_actions", []),
            remaining_actions=context.get("remaining_actions", []),
            resources=context.get("resources", {}),
            constraints=context.get("constraints", []),
            metadata=context,
        )
        
        # Re-plan
        result = await self.replanner.maybe_replan(replan_context)
        
        if result.success and result.new_plan_id:
            # Notify callback
            monitor = self._active_monitors.get(plan_id)
            if monitor and monitor["on_replan"]:
                await monitor["on_replan"](result.new_plan_id, result)
            
            logger.info(f"Auto-replan executed for {plan_id}: {result.changes_summary}")
            return result
        
        return None

    async def stop_monitoring_plan(self, plan_id: str) -> None:
        """Stop monitoring for a plan"""
        await self.drift_detector.stop_monitoring(plan_id)
        self._active_monitors.pop(plan_id, None)