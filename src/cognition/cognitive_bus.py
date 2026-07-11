"""
Cognitive Bus - Unified Event Bus for Cognitive Modules

Central event bus for all cognitive modules enabling decoupled communication
between reasoning, memory, planning, and agent components.
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class CognitiveEventType(Enum):
    """Standard cognitive event types"""
    # Planning events
    PLAN_CREATED = "plan.created"
    PLAN_STARTED = "plan.started"
    PLAN_COMPLETED = "plan.completed"
    PLAN_FAILED = "plan.failed"
    PLAN_REPLANNED = "plan.replanned"
    
    # Drift/Replanning events
    DRIFT_DETECTED = "drift.detected"
    REPLAN_TRIGGERED = "replan.triggered"
    REPLAN_COMPLETED = "replan.completed"
    
    # Memory events
    MEMORY_STORED = "memory.stored"
    MEMORY_RETRIEVED = "memory.retrieved"
    MEMORY_COMPRESSED = "memory.compressed"
    CHECKPOINT_CREATED = "checkpoint.created"
    CHECKPOINT_RESUMED = "checkpoint.resumed"
    
    # Agent/Delegation events
    AGENT_REGISTERED = "agent.registered"
    AGENT_DELEGATED = "agent.delegated"
    DELEGATION_COMPLETED = "delegation.completed"
    DELEGATION_FAILED = "delegation.failed"
    
    # Voice events
    USER_SPEECH = "user.speech"
    ASSISTANT_SPEECH = "assistant.speech"
    
    # Tool events
    TOOL_INVOKED = "tool.invoked"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"
    MCP_TOOL_DISCOVERED = "mcp.tool.discovered"
    
    # Learning/Improvement events
    REFLECTION_COMPLETED = "reflection.completed"
    STRATEGY_EVOLVED = "strategy.evolved"
    ARCHITECTURE_PATCH_PROPOSED = "architecture.patch.proposed"
    ARCHITECTURE_PATCH_APPLIED = "architecture.patch.applied"
    
    # System events
    SYSTEM_STARTED = "system.started"
    SYSTEM_SHUTDOWN = "system.shutdown"
    ERROR_OCCURRED = "error.occurred"
    METRICS_UPDATED = "metrics.updated"
    
    # Validation events
    VALIDATION_STARTED = "validation.started"
    VALIDATION_COMPLETED = "validation.completed"
    VALIDATION_FAILED = "validation.failed"
    ABLATION_STARTED = "ablation.started"
    ABLATION_COMPLETED = "ablation.completed"
    BENCHMARK_STARTED = "benchmark.started"
    BENCHMARK_COMPLETED = "benchmark.completed"
    COST_ANALYSIS_STARTED = "cost_analysis.started"
    COST_ANALYSIS_COMPLETED = "cost_analysis.completed"
    LONG_HORIZON_STARTED = "long_horizon.started"
    LONG_HORIZON_COMPLETED = "long_horizon.completed"


@dataclass
class CognitiveEvent:
    """Event on the cognitive bus"""
    event_type: CognitiveEventType
    source: str  # Component that emitted the event
    payload: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    correlation_id: Optional[str] = None  # For tracing related events
    metadata: Dict[str, Any] = field(default_factory=dict)


class CognitiveBus:
    """
    Central event bus for all cognitive modules.
    
    Features:
    - Async event emission with optional await for handlers
    - Event filtering and routing
    - Event history for debugging/replaybacktesting
    - Correlation ID tracking for distributed tracing
    - Priority-based handler execution
    """
    
    def __init__(self, max_history: int = 10000):
        self._subscribers: Dict[CognitiveEventType, List[Callable]] = defaultdict(list)
        self._wildcard_subscribers: List[Callable] = []  # Receive all events
        self._history: List[CognitiveEvent] = []
        self._max_history = max_history
        self._event_filters: Dict[str, Callable[[CognitiveEvent], bool]] = {}
        self._running = False
        self._processing_queue: asyncio.Queue = asyncio.Queue()
        self._processor_task: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """Start the event processor"""
        self._running = True
        self._processor_task = asyncio.create_task(self._process_queue())
        logger.info("CognitiveBus started")
        
    async def stop(self) -> None:
        """Stop the event processor"""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        logger.info("CognitiveBus stopped")
    
    def subscribe(
        self,
        event_type: CognitiveEventType,
        handler: Callable[[CognitiveEvent], Any],
        priority: int = 0,
        filter_fn: Optional[Callable[[CognitiveEvent], bool]] = None,
    ) -> str:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Event type to subscribe to
            handler: Async function to handle the event
            priority: Handler priority (higher = earlier execution)
            filter_fn: Optional filter function
            
        Returns:
            Subscription ID for unsubscribing
        """
        subscription_id = str(uuid.uuid4())
        
        # Store with priority
        self._subscribers[event_type].append({
            "id": subscription_id,
            "handler": handler,
            "priority": priority,
            "filter": filter_fn,
        })
        
        # Sort by priority (highest first)
        self._subscribers[event_type].sort(key=lambda x: x["priority"], reverse=True)
        
        logger.debug(f"Subscribed {subscription_id} to {event_type.value}")
        return subscription_id
    
    def subscribe_all(
        self,
        handler: Callable[[CognitiveEvent], Any],
        filter_fn: Optional[Callable[[CognitiveEvent], bool]] = None,
    ) -> str:
        """Subscribe to all events"""
        subscription_id = str(uuid.uuid4())
        self._wildcard_subscribers.append({
            "id": subscription_id,
            "handler": handler,
            "filter": filter_fn,
        })
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe by subscription ID"""
        # Check wildcard subscribers
        for i, sub in enumerate(self._wildcard_subscribers):
            if sub["id"] == subscription_id:
                self._wildcard_subscribers.pop(i)
                return True
        
        # Check typed subscribers
        for event_type, subs in self._subscribers.items():
            for i, sub in enumerate(subs):
                if sub["id"] == subscription_id:
                    subs.pop(i)
                    return True
        
        return False
    
    async def emit(self, event: CognitiveEvent) -> None:
        """
        Emit an event to all subscribers.
        
        Handlers are called in priority order. If any handler raises,
        the error is logged but other handlers continue.
        """
        # Add to history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        
        # Queue for async processing
        await self._processing_queue.put(event)
    
    async def emit_sync(self, event: CognitiveEvent) -> List[Any]:
        """
        Emit event and wait for all handlers to complete.
        
        Returns:
            List of handler results
        """
        results = []
        
        # Call typed subscribers
        for sub in self._subscribers.get(event.event_type, []):
            if sub["filter"] and not sub["filter"](event):
                continue
            try:
                result = await sub["handler"](event)
                results.append(result)
            except Exception as e:
                logger.error(f"Handler {sub['id']} failed for {event.event_type.value}: {e}")
        
        # Call wildcard subscribers
        for sub in self._wildcard_subscribers:
            if sub["filter"] and not sub["filter"](event):
                continue
            try:
                result = await sub["handler"](event)
                results.append(result)
            except Exception as e:
                logger.error(f"Wildcard handler {sub['id']} failed: {e}")
        
        return results
    
    async def _process_queue(self) -> None:
        """Process queued events"""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._processing_queue.get(),
                    timeout=1.0
                )
                await self.emit_sync(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Event processing error: {e}")
    
    def create_event(
        self,
        event_type: CognitiveEventType,
        source: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CognitiveEvent:
        """Create a new cognitive event"""
        return CognitiveEvent(
            event_type=event_type,
            source=source,
            payload=payload,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )
    
    def get_history(
        self,
        event_type: Optional[CognitiveEventType] = None,
        source: Optional[str] = None,
        since: Optional[float] = None,
        limit: int = 100,
    ) -> List[CognitiveEvent]:
        """Get event history with optional filters"""
        events = self._history
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if source:
            events = [e for e in events if e.source == source]
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        return events[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bus statistics"""
        return {
            "total_events": len(self._history),
            "subscribers_by_type": {
                et.value: len(subs) for et, subs in self._subscribers.items()
            },
            "wildcard_subscribers": len(self._wildcard_subscribers),
            "queue_size": self._processing_queue.qsize(),
            "running": self._running,
        }


# Global instance
_cognitive_bus: Optional[CognitiveBus] = None


def get_cognitive_bus() -> CognitiveBus:
    """Get the global cognitive bus instance"""
    global _cognitive_bus
    if _cognitive_bus is None:
        _cognitive_bus = CognitiveBus()
    return _cognitive_bus


async def initialize_cognitive_bus() -> CognitiveBus:
    """Initialize and start the global cognitive bus"""
    bus = get_cognitive_bus()
    await bus.start()
    return bus


async def shutdown_cognitive_bus() -> None:
    """Shutdown the global cognitive bus"""
    global _cognitive_bus
    if _cognitive_bus:
        await _cognitive_bus.stop()
        _cognitive_bus = None


# Convenience functions for common events
async def emit_plan_event(
    event_type: CognitiveEventType,
    plan_id: str,
    source: str,
    details: Dict[str, Any],
    correlation_id: Optional[str] = None,
) -> None:
    """Emit a plan-related event"""
    bus = get_cognitive_bus()
    event = bus.create_event(
        event_type=event_type,
        source=source,
        payload={"plan_id": plan_id, **details},
        correlation_id=correlation_id,
    )
    await bus.emit(event)


async def emit_drift_event(
    plan_id: str,
    drift_signals: List[Dict[str, Any]],
    source: str = "drift_detector",
) -> None:
    """Emit a drift detection event"""
    bus = get_cognitive_bus()
    event = bus.create_event(
        event_type=CognitiveEventType.DRIFT_DETECTED,
        source=source,
        payload={"plan_id": plan_id, "signals": drift_signals},
    )
    await bus.emit(event)


async def emit_memory_event(
    event_type: CognitiveEventType,
    agent_id: str,
    source: str,
    details: Dict[str, Any],
) -> None:
    """Emit a memory-related event"""
    bus = get_cognitive_bus()
    event = bus.create_event(
        event_type=event_type,
        source=source,
        payload={"agent_id": agent_id, **details},
    )
    await bus.emit(event)


async def emit_delegation_event(
    event_type: CognitiveEventType,
    delegator_id: str,
    delegatee_id: str,
    task_id: str,
    source: str,
    details: Dict[str, Any],
) -> None:
    """Emit a delegation event"""
    bus = get_cognitive_bus()
    event = bus.create_event(
        event_type=event_type,
        source=source,
        payload={
            "delegator_id": delegator_id,
            "delegatee_id": delegatee_id,
            "task_id": task_id,
            **details,
        },
    )
    await bus.emit(event)