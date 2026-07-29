"""
Agent Protocol - Structured messaging between agents

The AgentProtocol provides:
- Standardized message formats
- Message validation
- Message routing
- Conversation management
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of agent messages"""

    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    QUERY = "query"
    COMMAND = "command"
    STATUS = "status"
    ERROR = "error"


class MessagePriority(Enum):
    """Message priority levels"""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class AgentMessage:
    """A message between agents"""

    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.REQUEST
    sender: str = "unknown"
    receiver: str = "unknown"
    content: Dict[str, Any] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    ttl: Optional[float] = None  # Time to live

    def is_expired(self) -> bool:
        """Check if message has expired"""
        if self.ttl is None:
            return False
        return (datetime.now().timestamp() - self.timestamp) > self.ttl

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        """Create from dictionary"""
        return cls(
            message_id=data["message_id"],
            message_type=MessageType(data["message_type"]),
            sender=data["sender"],
            receiver=data["receiver"],
            content=data["content"],
            priority=MessagePriority(data["priority"]),
            timestamp=data["timestamp"],
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to"),
            ttl=data.get("ttl"),
        )


@dataclass
class Conversation:
    """A conversation between agents"""

    conversation_id: str
    participants: Set[str]
    messages: List[AgentMessage]
    started_at: float = field(default_factory=lambda: datetime.now().timestamp())
    last_activity: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, message: AgentMessage) -> None:
        """Add a message to the conversation"""
        self.messages.append(message)
        self.last_activity = datetime.now().timestamp()

    def get_messages(
        self,
        sender: Optional[str] = None,
        message_type: Optional[MessageType] = None,
    ) -> List[AgentMessage]:
        """Get filtered messages from conversation"""
        messages = self.messages

        if sender:
            messages = [m for m in messages if m.sender == sender]

        if message_type:
            messages = [m for m in messages if m.message_type == message_type]

        return messages


class AgentProtocol:
    """
    Protocol for structured agent communication.

    Provides:
    - Standardized message formats
    - Message validation
    - Conversation tracking
    - Reply management
    """

    def __init__(self):
        # Active conversations
        self._conversations: Dict[str, Conversation] = {}
        self._agent_conversations: Dict[str, Set[str]] = defaultdict(set)

        # Message history
        self._message_history: List[AgentMessage] = []
        self._max_history = 1000

        # Pending replies
        self._pending_replies: Dict[str, asyncio.Future] = {}

        # Statistics
        self._messages_sent = 0
        self._messages_received = 0
        self._conversations_created = 0

    async def initialize(self) -> None:
        """Initialize the agent protocol"""
        logger.info("AgentProtocol initialized")

    async def send_message(
        self,
        message: AgentMessage,
    ) -> str:
        """
        Send a message.

        Args:
            message: Message to send

        Returns:
            Message ID
        """
        # Validate message
        if not await self._validate_message(message):
            raise ValueError("Invalid message")

        # Add to history
        self._message_history.append(message)
        if len(self._message_history) > self._max_history:
            self._message_history.pop(0)

        # Add to conversation if correlation_id exists
        if message.correlation_id:
            await self._add_to_conversation(message)

        self._messages_sent += 1

        logger.debug(
            f"Sent message {message.message_id} from {message.sender} to {message.receiver}"
        )
        return message.message_id

    async def send_request(
        self,
        sender: str,
        receiver: str,
        content: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        timeout: float = 30.0,
    ) -> AgentMessage:
        """
        Send a request and wait for response.

        Args:
            sender: Sender agent ID
            receiver: Receiver agent ID
            content: Request content
            priority: Message priority
            timeout: Maximum time to wait for response

        Returns:
            Response message
        """
        correlation_id = str(uuid.uuid4())

        # Create request message
        request = AgentMessage(
            message_type=MessageType.REQUEST,
            sender=sender,
            receiver=receiver,
            content=content,
            priority=priority,
            correlation_id=correlation_id,
        )

        # Create future for response
        future = asyncio.Future()
        self._pending_replies[correlation_id] = future

        # Send request
        await self.send_message(request)

        try:
            # Wait for response
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            del self._pending_replies[correlation_id]
            raise TimeoutError(f"Request {correlation_id} timed out")

    async def send_response(
        self,
        sender: str,
        receiver: str,
        content: Dict[str, Any],
        reply_to: str,
        correlation_id: str,
    ) -> str:
        """
        Send a response to a request.

        Args:
            sender: Sender agent ID
            receiver: Receiver agent ID
            content: Response content
            reply_to: Original message ID
            correlation_id: Correlation ID

        Returns:
            Message ID
        """
        response = AgentMessage(
            message_type=MessageType.RESPONSE,
            sender=sender,
            receiver=receiver,
            content=content,
            reply_to=reply_to,
            correlation_id=correlation_id,
        )

        return await self.send_message(response)

    async def receive_message(self, message: AgentMessage) -> None:
        """
        Receive a message.

        Args:
            message: Received message
        """
        self._messages_received += 1

        # Add to history
        self._message_history.append(message)
        if len(self._message_history) > self._max_history:
            self._message_history.pop(0)

        # Add to conversation
        await self._add_to_conversation(message)

        # Handle response if waiting for reply
        if message.message_type == MessageType.RESPONSE and message.correlation_id:
            if message.correlation_id in self._pending_replies:
                future = self._pending_replies.pop(message.correlation_id)
                if not future.done():
                    future.set_result(message)

        logger.debug(f"Received message {message.message_id} from {message.sender}")

    async def _validate_message(self, message: AgentMessage) -> bool:
        """Validate a message"""
        # Check required fields
        if not message.sender or not message.receiver:
            return False

        # Check if expired
        if message.is_expired():
            return False

        return True

    async def _add_to_conversation(self, message: AgentMessage) -> None:
        """Add message to conversation"""
        conversation_id = message.correlation_id

        if conversation_id is None:
            return

        if conversation_id not in self._conversations:
            # Create new conversation
            conversation = Conversation(
                conversation_id=conversation_id,
                participants={message.sender, message.receiver},
            )
            self._conversations[conversation_id] = conversation
            self._conversations_created += 1

            # Track agent conversations
            self._agent_conversations[message.sender].add(conversation_id)
            self._agent_conversations[message.receiver].add(conversation_id)

        # Add message to conversation
        self._conversations[conversation_id].add_message(message)

    def get_conversation(
        self,
        conversation_id: str,
    ) -> Optional[Conversation]:
        """Get a conversation by ID"""
        return self._conversations.get(conversation_id)

    def get_agent_conversations(
        self,
        agent_id: str,
    ) -> List[Conversation]:
        """Get all conversations for an agent"""
        conversation_ids = self._agent_conversations.get(agent_id, set())
        return [self._conversations[cid] for cid in conversation_ids if cid in self._conversations]

    def get_message_history(
        self,
        sender: Optional[str] = None,
        receiver: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get message history"""
        messages = self._message_history

        if sender:
            messages = [m for m in messages if m.sender == sender]

        if receiver:
            messages = [m for m in messages if m.receiver == receiver]

        messages = messages[-limit:]
        return [m.to_dict() for m in messages]

    def get_metrics(self) -> Dict[str, Any]:
        """Get protocol metrics"""
        return {
            "messages_sent": self._messages_sent,
            "messages_received": self._messages_received,
            "conversations_created": self._conversations_created,
            "active_conversations": len(self._conversations),
            "pending_replies": len(self._pending_replies),
            "history_size": len(self._message_history),
        }
