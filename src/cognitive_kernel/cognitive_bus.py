"""
Cognitive Bus - Event-based communication system

The CognitiveBus provides:
- Event-driven communication between cognitive components
- Agent protocol for structured messaging
- Message brokering for agent coordination
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import json


logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of cognitive events"""
    COGNITIVE_PROCESSING = "cognitive_processing"
    ATTENTION_ALLOCATED = "attention_allocated"
    MEMORY_CONSOLIDATED = "memory_consolidated"
    REASONING_COMPLETED = "reasoning_completed"
    AGENT_MESSAGE = "agent_message"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    GOAL_ACHIEVED = "goal_achieved"
    IDENTITY_UPDATED = "identity_updated"
    SOCIETY_EVENT = "society_event"


@dataclass
class CognitiveEvent:
    """A cognitive event"""
    event_type: EventType
    data: Dict[str, Any]
    source: str
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    event_id: str = field(default_factory=lambda: f"evt_{datetime.now().timestamp()}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CognitiveEvent":
        """Create event from dictionary"""
        return cls(
            event_id=data["event_id"],
            event_type=EventType(data["event_type"]),
            data=data["data"],
            source=data["source"],
            timestamp=data["timestamp"],
        )


class CognitiveBus:
    """
    Event bus for cognitive communication.
    
    All agents communicate through:
    Event
     ↓
    Bus
     ↓
    Subscribers
    """
    
    def __init__(self, kernel: Any):
        self.kernel = kernel
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._lock = asyncio.Lock()
        
        # Event history for debugging and analysis
        self._event_history: List[CognitiveEvent] = []
        self._max_history = 1000
        
        # Metrics
        self._events_published = 0
        self._events_processed = 0
        self._events_failed = 0
    
    async def initialize(self) -> None:
        """Initialize the cognitive bus"""
        self._running = True
        asyncio.create_task(self._process_events())
        logger.info("CognitiveBus initialized")
    
    async def shutdown(self) -> None:
        """Shutdown the cognitive bus"""
        self._running = False
        
        # Process remaining events
        while not self._event_queue.empty():
            await self._event_queue.get()
        
        logger.info("CognitiveBus shutdown complete")
    
    async def emit(
        self,
        event_type: EventType | str,
        data: Dict[str, Any],
        source: str = "unknown",
    ) -> str:
        """
        Emit a cognitive event.
        
        Args:
            event_type: Type of the event
            data: Event data
            source: Source of the event
            
        Returns:
            Event ID
        """
        resolved_event_type = event_type if isinstance(event_type, EventType) else EventType(event_type)
        event = CognitiveEvent(
            event_type=resolved_event_type,
            data=data,
            source=source,
        )
        
        await self._event_queue.put(event)
        self._events_published += 1
        
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        logger.debug(f"Emitted event {event.event_id} of type {resolved_event_type.value}")
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
        """Dispatch event to all subscribers"""
        async with self._lock:
            subscribers = self._subscribers.get(event.event_type, []).copy()
        
        # Dispatch to all subscribers
        tasks = []
        for subscriber in subscribers:
            try:
                task = asyncio.create_task(subscriber(event))
                tasks.append(task)
            except Exception as e:
                logger.error(f"Error creating subscriber task: {e}")
        
        # Wait for all subscribers to process
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def subscribe(
        self,
        event_type: EventType,
        callback: Callable[[CognitiveEvent], Any],
    ) -> None:
        """
        Subscribe to a specific event type.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Callback function to handle the event
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        
        logger.debug(f"Subscribed to {event_type.value} events")
    
    def unsubscribe(
        self,
        event_type: EventType,
        callback: Callable[[CognitiveEvent], Any],
    ) -> None:
        """
        Unsubscribe from a specific event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            callback: Callback function to remove
        """
        if event_type in self._subscribers:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"Unsubscribed from {event_type.value} events")
    
    def get_event_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get event history.
        
        Args:
            event_type: Filter by event type (optional)
            limit: Maximum number of events to return
            
        Returns:
            List of event dictionaries
        """
        events = self._event_history
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        events = events[-limit:]
        return [e.to_dict() for e in events]
    
    def get_metrics(self) -> Dict[str, int]:
        """Get bus metrics"""
        return {
            "events_published": self._events_published,
            "events_processed": self._events_processed,
            "events_failed": self._events_failed,
            "queue_size": self._event_queue.qsize(),
            "subscribers": sum(len(subs) for subs in self._subscribers.values()),
        }
