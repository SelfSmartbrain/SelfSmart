"""
Message Broker - Central message routing and coordination

The MessageBroker provides:
- Message routing between agents
- Message queuing and delivery
- Load balancing
- Dead letter queue for failed messages
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import heapq


logger = logging.getLogger(__name__)


class DeliveryStatus(Enum):
    """Message delivery status"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class QueuedMessage:
    """A message in the queue"""
    message: Any
    priority: int
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    attempts: int = 0
    max_attempts: int = 3
    status: DeliveryStatus = DeliveryStatus.PENDING
    
    def __lt__(self, other: "QueuedMessage") -> bool:
        """Compare for priority queue (lower priority number = higher priority)"""
        return self.priority < other.priority


@dataclass
class AgentSubscription:
    """An agent subscription to a topic"""
    agent_id: str
    topic: str
    callback: Callable[[Any], Any]
    active: bool = True


class MessageBroker:
    """
    Central message broker for agent communication.
    
    Provides:
    - Topic-based pub/sub messaging
    - Point-to-point messaging
    - Message queuing and delivery
    - Load balancing
    - Dead letter queue
    """
    
    def __init__(
        self,
        max_queue_size: int = 1000,
        max_delivery_attempts: int = 3,
    ):
        self.max_queue_size = max_queue_size
        self.max_delivery_attempts = max_delivery_attempts
        
        # Topic subscriptions
        self._subscriptions: Dict[str, List[AgentSubscription]] = {}
        
        # Point-to-point queues
        self._agent_queues: Dict[str, List[QueuedMessage]] = {}
        
        # Priority queue for global processing
        self._priority_queue: List[QueuedMessage] = []
        
        # Dead letter queue
        self._dead_letter_queue: List[QueuedMessage] = []
        
        # Delivery tracking
        self._delivery_status: Dict[str, DeliveryStatus] = {}
        
        # Processing
        self._running = False
        self._lock = asyncio.Lock()
        
        # Statistics
        self._messages_published = 0
        self._messages_delivered = 0
        self._messages_failed = 0
        self._messages_expired = 0
    
    async def initialize(self) -> None:
        """Initialize the message broker"""
        self._running = True
        asyncio.create_task(self._process_queues())
        logger.info("MessageBroker initialized")
    
    async def shutdown(self) -> None:
        """Shutdown the message broker"""
        self._running = False
        logger.info("MessageBroker shutdown complete")
    
    async def publish(
        self,
        topic: str,
        message: Any,
        priority: int = 5,
    ) -> int:
        """
        Publish a message to a topic.
        
        Args:
            topic: Topic to publish to
            message: Message to publish
            priority: Message priority (0-10, lower = higher priority)
            
        Returns:
            Number of subscribers notified
        """
        async with self._lock:
            if topic not in self._subscriptions:
                return 0
            
            subscribers = [sub for sub in self._subscriptions[topic] if sub.active]
            
            if not subscribers:
                return 0
            
            # Deliver to all subscribers
            delivered = 0
            for subscription in subscribers:
                try:
                    result = subscription.callback(message)
                    if asyncio.iscoroutine(result):
                        await result
                    delivered += 1
                except Exception as e:
                    logger.error(f"Error delivering to {subscription.agent_id}: {e}")
            
            self._messages_published += 1
            self._messages_delivered += delivered
            
            logger.debug(f"Published to topic {topic}: {delivered} subscribers notified")
            return delivered
    
    async def subscribe(
        self,
        agent_id: str,
        topic: str,
        callback: Callable[[Any], Any],
    ) -> bool:
        """
        Subscribe an agent to a topic.
        
        Args:
            agent_id: Agent identifier
            topic: Topic to subscribe to
            callback: Callback function
            
        Returns:
            True if subscribed successfully
        """
        async with self._lock:
            subscription = AgentSubscription(
                agent_id=agent_id,
                topic=topic,
                callback=callback,
            )
            
            if topic not in self._subscriptions:
                self._subscriptions[topic] = []
            
            self._subscriptions[topic].append(subscription)
            
            logger.debug(f"Subscribed {agent_id} to topic {topic}")
            return True
    
    async def unsubscribe(
        self,
        agent_id: str,
        topic: str,
    ) -> bool:
        """
        Unsubscribe an agent from a topic.
        
        Args:
            agent_id: Agent identifier
            topic: Topic to unsubscribe from
            
        Returns:
            True if unsubscribed successfully
        """
        async with self._lock:
            if topic not in self._subscriptions:
                return False
            
            # Find and deactivate subscription
            for sub in self._subscriptions[topic]:
                if sub.agent_id == agent_id:
                    sub.active = False
                    self._subscriptions[topic].remove(sub)
                    logger.debug(f"Unsubscribed {agent_id} from topic {topic}")
                    return True
            
            return False
    
    async def send_to_agent(
        self,
        agent_id: str,
        message: Any,
        priority: int = 5,
    ) -> bool:
        """
        Send a message directly to an agent.
        
        Args:
            agent_id: Target agent ID
            message: Message to send
            priority: Message priority
            
        Returns:
            True if queued successfully
        """
        async with self._lock:
            if agent_id not in self._agent_queues:
                self._agent_queues[agent_id] = []
            
            # Check queue size
            if len(self._agent_queues[agent_id]) >= self.max_queue_size:
                logger.warning(f"Queue for {agent_id} is full")
                return False
            
            # Add to queue
            queued_msg = QueuedMessage(
                message=message,
                priority=priority,
                max_attempts=self.max_delivery_attempts,
            )
            
            self._agent_queues[agent_id].append(queued_msg)
            
            # Also add to priority queue for processing
            heapq.heappush(self._priority_queue, queued_msg)
            
            self._messages_published += 1
            
            logger.debug(f"Queued message for {agent_id} (priority: {priority})")
            return True
    
    async def receive_from_agent(
        self,
        agent_id: str,
        timeout: float = 5.0,
    ) -> Optional[Any]:
        """
        Receive a message for an agent.
        
        Args:
            agent_id: Agent identifier
            timeout: Maximum time to wait
            
        Returns:
            Message or None if timeout
        """
        start = datetime.now().timestamp()
        
        while (datetime.now().timestamp() - start) < timeout:
            async with self._lock:
                if agent_id in self._agent_queues and self._agent_queues[agent_id]:
                    queued_msg = self._agent_queues[agent_id].pop(0)
                    queued_msg.status = DeliveryStatus.DELIVERED
                    self._messages_delivered += 1
                    return queued_msg.message
            
            await asyncio.sleep(0.1)
        
        return None
    
    async def _process_queues(self) -> None:
        """Process message queues"""
        while self._running:
            try:
                async with self._lock:
                    if self._priority_queue:
                        queued_msg = heapq.heappop(self._priority_queue)
                        
                        # Check if already delivered
                        if queued_msg.status == DeliveryStatus.DELIVERED:
                            continue
                        
                        # Check if expired
                        if queued_msg.attempts >= queued_msg.max_attempts:
                            queued_msg.status = DeliveryStatus.FAILED
                            self._dead_letter_queue.append(queued_msg)
                            self._messages_failed += 1
                            logger.warning(f"Message failed after {queued_msg.attempts} attempts")
                            continue
                        
                        queued_msg.attempts += 1
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error processing queue: {e}")
                await asyncio.sleep(0.1)
    
    def get_topic_subscribers(self, topic: str) -> List[str]:
        """Get subscribers for a topic"""
        if topic not in self._subscriptions:
            return []
        
        return [sub.agent_id for sub in self._subscriptions[topic] if sub.active]
    
    def get_agent_queue_size(self, agent_id: str) -> int:
        """Get queue size for an agent"""
        return len(self._agent_queues.get(agent_id, []))
    
    def get_dead_letter_queue(self) -> List[Dict[str, Any]]:
        """Get dead letter queue"""
        return [
            {
                "message": msg.message,
                "priority": msg.priority,
                "attempts": msg.attempts,
                "timestamp": msg.timestamp,
            }
            for msg in self._dead_letter_queue
        ]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get broker metrics"""
        return {
            "messages_published": self._messages_published,
            "messages_delivered": self._messages_delivered,
            "messages_failed": self._messages_failed,
            "messages_expired": self._messages_expired,
            "active_topics": len(self._subscriptions),
            "total_subscriptions": sum(
                len(subs) for subs in self._subscriptions.values()
            ),
            "agent_queues": len(self._agent_queues),
            "priority_queue_size": len(self._priority_queue),
            "dead_letter_queue_size": len(self._dead_letter_queue),
        }
