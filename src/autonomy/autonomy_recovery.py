"""Autonomy recovery with failure-type-specific logic.

Phase 16C: Autonomy Recovery

Implements intelligent recovery from agentic failures with:
- Failure type classification
- Type-specific recovery strategies
- Retry with backoff
- Alternative strategy selection
- Escalation to human oversight
"""

from __future__ import annotations

import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta

from src.config.logging import get_logger

logger = get_logger(__name__)


class FailureType(str, Enum):
    """Types of failures that can occur during autonomous execution."""
    
    # Resource failures
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    
    # Task execution failures
    TOOL_FAILURE = "tool_failure"
    TOOL_UNAVAILABLE = "tool_unavailable"
    INVALID_TOOL_INPUT = "invalid_tool_input"
    
    # Cognitive failures
    LLM_ERROR = "llm_error"
    CONTEXT_OVERFLOW = "context_overflow"
    PARSING_ERROR = "parsing_error"
    
    # Strategy failures
    PLAN_INVALID = "plan_invalid"
    PLAN_INFEASIBLE = "plan_infeasible"
    STRATEGY_FAILURE = "strategy_failure"
    
    # External failures
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    DEPENDENCY_FAILURE = "dependency_failure"
    
    # Unknown
    UNKNOWN = "unknown"


class RecoveryStrategy(str, Enum):
    """Recovery strategies for different failure types."""
    
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    RETRY_IMMEDIATE = "retry_immediate"
    ALTERNATIVE_TOOL = "alternative_tool"
    ALTERNATIVE_STRATEGY = "alternative_strategy"
    REDUCE_COMPLEXITY = "reduce_complexity"
    REQUEST_HUMAN_INTERVENTION = "request_human_intervention"
    SKIP_AND_CONTINUE = "skip_and_continue"
    ESCALATE = "escalate"


@dataclass
class FailureContext:
    """Context about a failure that occurred."""
    
    failure_type: FailureType
    error_message: str
    exception_type: Optional[str] = None
    traceback: Optional[str] = None
    objective_id: Optional[str] = None
    task_id: Optional[str] = None
    tool_name: Optional[str] = None
    retry_count: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_type": self.failure_type.value,
            "error_message": self.error_message,
            "exception_type": self.exception_type,
            "traceback": self.traceback,
            "objective_id": self.objective_id,
            "task_id": self.task_id,
            "tool_name": self.tool_name,
            "retry_count": self.retry_count,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class RecoveryAction:
    """A recovery action to take."""
    
    strategy: RecoveryStrategy
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    requires_human_approval: bool = False
    estimated_recovery_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "description": self.description,
            "parameters": self.parameters,
            "requires_human_approval": self.requires_human_approval,
            "estimated_recovery_time": self.estimated_recovery_time,
        }


class AutonomyRecovery:
    """Handles autonomous recovery from failures with type-specific logic."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_backoff_seconds: float = 1.0,
        max_backoff_seconds: float = 60.0,
    ):
        self.max_retries = max_retries
        self.base_backoff_seconds = base_backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self.failure_history: List[FailureContext] = []
        self.recovery_history: List[Dict[str, Any]] = []
        
        # Failure type to recovery strategy mapping
        self.failure_strategy_map = {
            FailureType.RESOURCE_EXHAUSTION: [
                RecoveryStrategy.REDUCE_COMPLEXITY,
                RecoveryStrategy.RETRY_WITH_BACKOFF,
                RecoveryStrategy.REQUEST_HUMAN_INTERVENTION,
            ],
            FailureType.TIMEOUT: [
                RecoveryStrategy.RETRY_WITH_BACKOFF,
                RecoveryStrategy.REDUCE_COMPLEXITY,
                RecoveryStrategy.ALTERNATIVE_STRATEGY,
            ],
            FailureType.RATE_LIMIT: [
                RecoveryStrategy.RETRY_WITH_BACKOFF,
                RecoveryStrategy.REQUEST_HUMAN_INTERVENTION,
            ],
            FailureType.TOOL_FAILURE: [
                RecoveryStrategy.RETRY_IMMEDIATE,
                RecoveryStrategy.ALTERNATIVE_TOOL,
                RecoveryStrategy.REQUEST_HUMAN_INTERVENTION,
            ],
            FailureType.TOOL_UNAVAILABLE: [
                RecoveryStrategy.ALTERNATIVE_TOOL,
                RecoveryStrategy.SKIP_AND_CONTINUE,
                RecoveryStrategy.REQUEST_HUMAN_INTERVENTION,
            ],
            FailureType.INVALID_TOOL_INPUT: [
                RecoveryStrategy.REDUCE_COMPLEXITY,
                RecoveryStrategy.REQUEST_HUMAN_INTERVENTION,
                RecoveryStrategy.SKIP_AND_CONTINUE,
            ],
            FailureType.LLM_ERROR: [
                RecoveryStrategy.RETRY_WITH_BACKOFF,
                RecoveryStrategy.REDUCE_COMPLEXITY,
                RecoveryStrategy.REQUEST_HUMAN_INTERVENTION,
            ],
            FailureType.CONTEXT_OVERFLOW: [
                RecoveryStrategy.REDUCE_COMPLEXITY,
                RecoveryStrategy.ALTERNATIVE_STRATEGY,
            ],
            FailureType.PARSING_ERROR: [
                RecoveryStrategy.RETRY_IMMEDIATE,
                RecoveryStrategy.REDUCE_COMPLEXITY,
            ],
            FailureType.PLAN_INVALID: [
                RecoveryStrategy.ALTERNATIVE_STRATEGY,
                RecoveryStrategy.REQUEST_HUMAN_INTERVENTION,
            ],
            FailureType.PLAN_INFEASIBLE: [
                RecoveryStrategy.ALTERNATIVE_STRATEGY,
                RecoveryStrategy.REDUCE_COMPLEXITY,
                RecoveryStrategy.REQUEST_HUMAN_INTERVENTION,
            ],
            FailureType.STRATEGY_FAILURE: [
                RecoveryStrategy.ALTERNATIVE_STRATEGY,
                RecoveryStrategy.REQUEST_HUMAN_INTERVENTION,
            ],
            FailureType.API_ERROR: [
                RecoveryStrategy.RETRY_WITH_BACKOFF,
                RecoveryStrategy.REQUEST_HUMAN_INTERVENTION,
            ],
            FailureType.NETWORK_ERROR: [
                RecoveryStrategy.RETRY_WITH_BACKOFF,
                RecoveryStrategy.REQUEST_HUMAN_INTERVENTION,
            ],
            FailureType.DEPENDENCY_FAILURE: [
                RecoveryStrategy.SKIP_AND_CONTINUE,
                RecoveryStrategy.REQUEST_HUMAN_INTERVENTION,
            ],
            FailureType.UNKNOWN: [
                RecoveryStrategy.REQUEST_HUMAN_INTERVENTION,
            ],
        }
        
        logger.info("AutonomyRecovery initialized")
    
    def classify_failure(
        self,
        error_message: str,
        exception_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FailureType:
        """Classify a failure into a specific type based on error message and context."""
        context = context or {}
        error_lower = error_message.lower()
        
        # Resource failures
        if "out of memory" in error_lower or "memory" in error_lower:
            return FailureType.RESOURCE_EXHAUSTION
        if "timeout" in error_lower or "timed out" in error_lower:
            return FailureType.TIMEOUT
        if "rate limit" in error_lower or "too many requests" in error_lower:
            return FailureType.RATE_LIMIT
        
        # Tool failures
        if "tool" in error_lower and "failed" in error_lower:
            return FailureType.TOOL_FAILURE
        if "tool not found" in error_lower or "unavailable" in error_lower:
            return FailureType.TOOL_UNAVAILABLE
        if "invalid input" in error_lower or "validation" in error_lower:
            return FailureType.INVALID_TOOL_INPUT
        
        # Cognitive failures
        if "llm" in error_lower or "openai" in error_lower or "anthropic" in error_lower:
            return FailureType.LLM_ERROR
        if "context" in error_lower and "exceed" in error_lower:
            return FailureType.CONTEXT_OVERFLOW
        if "parse" in error_lower or "json" in error_lower:
            return FailureType.PARSING_ERROR
        
        # Strategy failures
        if "plan" in error_lower and ("invalid" in error_lower or "failed" in error_lower):
            return FailureType.PLAN_INVALID
        if "infeasible" in error_lower:
            return FailureType.PLAN_INFEASIBLE
        if "strategy" in error_lower and "failed" in error_lower:
            return FailureType.STRATEGY_FAILURE
        
        # External failures
        if "api" in error_lower and "error" in error_lower:
            return FailureType.API_ERROR
        if "network" in error_lower or "connection" in error_lower:
            return FailureType.NETWORK_ERROR
        if "dependency" in error_lower:
            return FailureType.DEPENDENCY_FAILURE
        
        # Check exception type
        if exception_type:
            if "timeout" in exception_type.lower():
                return FailureType.TIMEOUT
            if "memory" in exception_type.lower():
                return FailureType.RESOURCE_EXHAUSTION
            if "connection" in exception_type.lower():
                return FailureType.NETWORK_ERROR
        
        # Default to unknown
        return FailureType.UNKNOWN
    
    def determine_recovery_action(
        self,
        failure_context: FailureContext,
    ) -> RecoveryAction:
        """Determine the appropriate recovery action for a failure."""
        
        # Get available strategies for this failure type
        strategies = self.failure_strategy_map.get(
            failure_context.failure_type,
            [RecoveryStrategy.REQUEST_HUMAN_INTERVENTION],
        )
        
        retry_count = failure_context.retry_count
        retry_strategies = {
            RecoveryStrategy.RETRY_IMMEDIATE,
            RecoveryStrategy.RETRY_WITH_BACKOFF,
        }
        primary_strategy = strategies[0]

        if primary_strategy in retry_strategies and retry_count <= self.max_retries:
            strategy = primary_strategy
        else:
            non_retry_strategies = [
                candidate for candidate in strategies if candidate not in retry_strategies
            ]
            if primary_strategy in retry_strategies:
                strategy_index = retry_count - self.max_retries - 1
            else:
                strategy_index = retry_count

            if strategy_index >= len(non_retry_strategies):
                return RecoveryAction(
                    strategy=RecoveryStrategy.ESCALATE,
                    description="All recovery strategies exhausted, escalating to human oversight",
                    requires_human_approval=True,
                )
            strategy = non_retry_strategies[strategy_index]
        
        # Build recovery action based on strategy
        if strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
            backoff = self._calculate_backoff(retry_count)
            return RecoveryAction(
                strategy=strategy,
                description=f"Retry operation with exponential backoff ({backoff:.1f}s)",
                parameters={"backoff_seconds": backoff},
                estimated_recovery_time=backoff,
            )
        
        elif strategy == RecoveryStrategy.RETRY_IMMEDIATE:
            return RecoveryAction(
                strategy=strategy,
                description="Retry operation immediately",
                estimated_recovery_time=0.0,
            )
        
        elif strategy == RecoveryStrategy.ALTERNATIVE_TOOL:
            return RecoveryAction(
                strategy=strategy,
                description=f"Try alternative tool instead of {failure_context.tool_name}",
                parameters={"original_tool": failure_context.tool_name},
                requires_human_approval=True,
            )
        
        elif strategy == RecoveryStrategy.ALTERNATIVE_STRATEGY:
            return RecoveryAction(
                strategy=strategy,
                description="Try alternative execution strategy",
                requires_human_approval=True,
            )
        
        elif strategy == RecoveryStrategy.REDUCE_COMPLEXITY:
            return RecoveryAction(
                strategy=strategy,
                description="Reduce task complexity and retry",
                parameters={"complexity_reduction": 0.5},
            )
        
        elif strategy == RecoveryStrategy.REQUEST_HUMAN_INTERVENTION:
            return RecoveryAction(
                strategy=strategy,
                description="Request human intervention for this failure",
                requires_human_approval=True,
            )
        
        elif strategy == RecoveryStrategy.SKIP_AND_CONTINUE:
            return RecoveryAction(
                strategy=strategy,
                description="Skip this task and continue with next objective",
            )
        
        elif strategy == RecoveryStrategy.ESCALATE:
            return RecoveryAction(
                strategy=strategy,
                description="Escalate to human oversight due to repeated failures",
                requires_human_approval=True,
            )
        
        else:
            return RecoveryAction(
                strategy=RecoveryStrategy.REQUEST_HUMAN_INTERVENTION,
                description="Unknown strategy, requesting human intervention",
                requires_human_approval=True,
            )
    
    def _calculate_backoff(self, retry_count: int) -> float:
        """Calculate exponential backoff time."""
        backoff = self.base_backoff_seconds * (2 ** retry_count)
        return min(backoff, self.max_backoff_seconds)
    
    async def execute_recovery(
        self,
        failure_context: FailureContext,
        recovery_action: RecoveryAction,
    ) -> Dict[str, Any]:
        """Execute a recovery action."""
        
        logger.info(
            f"Executing recovery: {recovery_action.strategy.value} for "
            f"{failure_context.failure_type.value}"
        )
        
        recovery_result = {
            "success": False,
            "action_taken": recovery_action.to_dict(),
            "failure_context": failure_context.to_dict(),
            "executed_at": datetime.utcnow().isoformat(),
        }
        
        try:
            if recovery_action.strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
                backoff = recovery_action.parameters.get("backoff_seconds", 1.0)
                await asyncio.sleep(backoff)
                recovery_result["success"] = True
                recovery_result["message"] = f"Waited {backoff:.1f}s for backoff"
            
            elif recovery_action.strategy == RecoveryStrategy.RETRY_IMMEDIATE:
                recovery_result["success"] = True
                recovery_result["message"] = "Immediate retry ready"
            
            elif recovery_action.strategy == RecoveryStrategy.REDUCE_COMPLEXITY:
                recovery_result["success"] = True
                recovery_result["message"] = "Complexity reduction applied"
                recovery_result["parameters"] = recovery_action.parameters
            
            elif recovery_action.strategy == RecoveryStrategy.SKIP_AND_CONTINUE:
                recovery_result["success"] = True
                recovery_result["message"] = "Task skipped, ready to continue"
            
            elif recovery_action.strategy in [
                RecoveryStrategy.ALTERNATIVE_TOOL,
                RecoveryStrategy.ALTERNATIVE_STRATEGY,
                RecoveryStrategy.REQUEST_HUMAN_INTERVENTION,
                RecoveryStrategy.ESCALATE,
            ]:
                recovery_result["success"] = True
                recovery_result["message"] = f"Recovery action requires: {recovery_action.strategy.value}"
                recovery_result["requires_action"] = True
            
            else:
                recovery_result["message"] = f"Unknown recovery strategy: {recovery_action.strategy}"
        
        except Exception as exc:
            recovery_result["message"] = f"Recovery execution failed: {exc}"
            logger.error(f"Recovery execution failed: {exc}")
        
        # Record recovery history
        self.recovery_history.append(recovery_result)
        
        return recovery_result
    
    async def handle_failure(
        self,
        error_message: str,
        exception_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Handle a failure end-to-end: classify, determine action, execute recovery."""
        
        context = context or {}
        retry_count = context.get("retry_count")
        if retry_count is None:
            attempt = context.get("attempt")
            retry_count = max(int(attempt) - 1, 0) if attempt is not None else 0
        
        # Classify failure
        failure_type = self.classify_failure(error_message, exception_type, context)
        
        # Create failure context
        failure_context = FailureContext(
            failure_type=failure_type,
            error_message=error_message,
            exception_type=exception_type,
            objective_id=context.get("objective_id"),
            task_id=context.get("task_id"),
            tool_name=context.get("tool_name"),
            retry_count=retry_count,
            metadata=context,
        )
        
        # Record failure history
        self.failure_history.append(failure_context)
        
        # Determine recovery action
        recovery_action = self.determine_recovery_action(failure_context)
        
        # Execute recovery
        recovery_result = await self.execute_recovery(failure_context, recovery_action)
        
        return {
            "failure_context": failure_context.to_dict(),
            "recovery_action": recovery_action.to_dict(),
            "recovery_result": recovery_result,
            "should_retry": recovery_action.strategy in [
                RecoveryStrategy.RETRY_IMMEDIATE,
                RecoveryStrategy.RETRY_WITH_BACKOFF,
            ],
        }
    
    def get_failure_statistics(self) -> Dict[str, Any]:
        """Get statistics about failures and recoveries."""
        if not self.failure_history:
            return {"total_failures": 0}
        
        failure_types = {}
        for failure in self.failure_history:
            ftype = failure.failure_type.value
            failure_types[ftype] = failure_types.get(ftype, 0) + 1
        
        successful_recoveries = sum(
            1 for r in self.recovery_history if r.get("success", False)
        )
        
        return {
            "total_failures": len(self.failure_history),
            "failures_by_type": failure_types,
            "total_recovery_attempts": len(self.recovery_history),
            "successful_recoveries": successful_recoveries,
            "recovery_success_rate": successful_recoveries / len(self.recovery_history)
            if self.recovery_history else 0.0,
        }
