"""
Cognitive Event System - Event-driven communication

The CognitiveEventSystem provides:
- Event definition and emission
- Event subscription and handling
- Event filtering and routing
- Event history and analysis
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import json


logger = logging.getLogger(__name__)


class CognitiveEventType(Enum):
    """Types of cognitive events"""
    # Attention events
    ATTENTION_ALLOCATED = "attention_allocated"
    ATTENTION_RELEASED = "attention_released"
    FOCUS_SHIFTED = "focus_shifted"
    
    # Memory events
    MEMORY_STORED = "memory_stored"
    MEMORY_RETRIEVED = "memory_retrieved"
    MEMORY_CONSOLIDATED = "memory_consolidated"
    MEMORY_FORGOTTEN = "memory_forgotten"
    
    # Reasoning events
    REASONING_STARTED = "reasoning_started"
    REASONING_COMPLETED = "reasoning_completed"
    REASONING_FAILED = "reasoning_failed"
    DECISION_MADE = "decision_made"
    
    # Agent events
    AGENT_BORN = "agent_born"
    AGENT_DIED = "agent_died"
    AGENT_MESSAGE = "agent_message"
    AGENT_TASK_ASSIGNED = "agent_task_assigned"
    AGENT_TASK_COMPLETED = "agent_task_completed"
    
    # Society events
    SOCIETY_FORMED = "society_formed"
    SOCIETY_DISSOLVED = "society_dissolved"
    COLLABORATION_STARTED = "collaboration_started"
    COLLABORATION_ENDED = "collaboration_ended"
    
    # Identity events
    IDENTITY_UPDATED = "identity_updated"
    MISSION_STARTED = "mission_started"
    MISSION_COMPLETED = "mission_completed"
    MISSION_FAILED = "mission_failed"
    
    # System events
    SYSTEM_INITIALIZED = "system_initialized"
    SYSTEM_SHUTDOWN = "system_shutdown"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class CognitiveEvent:
    """A cognitive event"""
    event_type: CognitiveEventType
    source: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    event_id: str = field(default_factory=lambda: f"evt_{datetime.now().timestamp()}")
    correlation_id: Optional[str] = None  # For event chains
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CognitiveEvent":
        """Create from dictionary"""
        return cls(
            event_id=data["event_id"],
            event_type=CognitiveEventType(data["event_type"]),
            source=data["source"],
            data=data["data"],
            timestamp=data["timestamp"],
            correlation_id=data.get("correlation_id"),
        )


@dataclass
class EventSubscription:
    """An event subscription"""
    event_type: CognitiveEventType
    callback: Callable[[CognitiveEvent], Any]
    filter_func: Optional[Callable[[CognitiveEvent], bool]] = None
    subscriber_id: str = "unknown"
    active: bool = True


class CognitiveEventSystem:
    """
    Event-driven communication system for cognitive components.
    
    Provides:
    - Event emission and broadcasting
    - Event subscription and filtering
    - Event chaining and correlation
    - Event history and analysis
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        
        # Subscriptions
        self._subscriptions: Dict[CognitiveEventType, List[EventSubscription]] = {}
        self._wildcard_subscriptions: List[EventSubscription] = []
        
        # Event history
        self._event_history: List[CognitiveEvent] = []
        
        # Event queue for async processing
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        
        # Statistics
        self._events_emitted = 0
        self._events_processed = 0
        self._events_failed = 0
    
    async def initialize(self) -> None:
        """Initialize the event system"""
        self._running = True
        asyncio.create_task(self._process_events())
        logger.info("CognitiveEventSystem initialized")
    
    async def shutdown(self) -> None:
        """Shutdown the event system"""
        self._running = False
        
        # Process remaining events
        while not self._event_queue.empty():
            await self._event_queue.get()
        
        logger.info("CognitiveEventSystem shutdown complete")
    
    async def emit(
        self,
        event_type: CognitiveEventType,
        source: str,
        data: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> str:
        """
        Emit a cognitive event.
        
        Args:
            event_type: Type of event
            source: Source of the event
            data: Event data
            correlation_id: Correlation ID for event chains
            
        Returns:
            Event ID
        """
        event = CognitiveEvent(
            event_type=event_type,
            source=source,
            data=data or {},
            correlation_id=correlation_id,
        )
        
        await self._event_queue.put(event)
        self._events_emitted += 1
        
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self.max_history:
            self._event_history.pop(0)
        
        logger.debug(f"Emitted event {event.event_id}: {event_type.value}")
        return event.event_id
    
    async def _process_events(self) -> None:
        """Process events from the queue"""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=0.1,
                )
                
                await self._dispatch_event(event)
                self._events_processed += 1
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                self._events_failed += 1
    
    async def _dispatch_event(self, event: CognitiveEvent) -> None:
        """Dispatch event to subscribers"""
        # Get relevant subscriptions
        subscriptions = []
        
        # Wildcard subscriptions
        subscriptions.extend(self._wildcard_subscriptions)
        
        # Type-specific subscriptions
        if event.event_type in self._subscriptions:
            subscriptions.extend(self._subscriptions[event.event_type])
        
        # Filter active subscriptions
        subscriptions = [sub for sub in subscriptions if sub.active]
        
        # Apply filters
        for sub in subscriptions:
            if sub.filter_func and not sub.filter_func(event):
                continue
            
            # Dispatch to subscriber
            try:
                result = sub.callback(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error in subscriber {sub.subscriber_id}: {e}")
    
    def subscribe(
        self,
        event_type: CognitiveEventType,
        callback: Callable[[CognitiveEvent], Any],
        subscriber_id: str = "unknown",
        filter_func: Optional[Callable[[CognitiveEvent], bool]] = None,
    ) -> str:
        """
        Subscribe to a specific event type.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Callback function
            subscriber_id: Subscriber identifier
            filter_func: Optional filter function
            
        Returns:
            Subscription ID
        """
        subscription = EventSubscription(
            event_type=event_type,
            callback=callback,
            filter_func=filter_func,
            subscriber_id=subscriber_id,
        )
        
        if event_type not in self._subscriptions:
            self._subscriptions[event_type] = []
        
        self._subscriptions[event_type].append(subscription)
        
        logger.debug(f"Subscribed {subscriber_id} to {event_type.value}")
        return f"{subscriber_id}_{event_type.value}"
    
    def subscribe_wildcard(
        self,
        callback: Callable[[CognitiveEvent], Any],
        subscriber_id: str = "unknown",
        filter_func: Optional[Callable[[CognitiveEvent], bool]] = None,
    ) -> str:
        """
        Subscribe to all events.
        
        Args:
            callback: Callback function
            subscriber_id: Subscriber identifier
            filter_func: Optional filter function
            
        Returns:
            Subscription ID
        """
        subscription = EventSubscription(
            event_type=CognitiveEventType.ATTENTION_ALLOCATED,  # Dummy type
            callback=callback,
            filter_func=filter_func,
            subscriber_id=subscriber_id,
        )
        
        self._wildcard_subscriptions.append(subscription)
        
        logger.debug(f"Subscribed {subscriber_id} to all events")
        return f"{subscriber_id}_wildcard"
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from events.
        
        Args:
            subscription_id: Subscription ID
            
        Returns:
            True if unsubscribed successfully
        """
        # Search in type-specific subscriptions
        for event_type, subscriptions in self._subscriptions.items():
            for i, sub in enumerate(subscriptions):
                if f"{sub.subscriber_id}_{event_type.value}" == subscription_id:
                    sub.active = False
                    subscriptions.pop(i)
                    logger.debug(f"Unsubscribed {subscription_id}")
                    return True
        
        # Search in wildcard subscriptions
        for i, sub in enumerate(self._wildcard_subscriptions):
            if f"{sub.subscriber_id}_wildcard" == subscription_id:
                sub.active = False
                self._wildcard_subscriptions.pop(i)
                logger.debug(f"Unsubscribed {subscription_id}")
                return True
        
        return False
    
    def get_event_history(
        self,
        event_type: Optional[CognitiveEventType] = None,
        source: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get event history.
        
        Args:
            event_type: Filter by event type
            source: Filter by source
            limit: Maximum number of events
            
        Returns:
            List of event dictionaries
        """
        events = self._event_history
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if source:
            events = [e for e in events if e.source == source]
        
        events = events[-limit:]
        return [e.to_dict() for e in events]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get event system metrics"""
        return {
            "events_emitted": self._events_emitted,
            "events_processed": self._events_processed,
            "events_failed": self._events_failed,
            "queue_size": self._event_queue.qsize(),
            "history_size": len(self._event_history),
            "active_subscriptions": sum(
                len(subs) for subs in self._subscriptions.values()
            ) + len(self._wildcard_subscriptions),
        }
