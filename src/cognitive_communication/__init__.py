"""
Cognitive Communication Bus - Phase 13

The Cognitive Communication Bus provides:
- Event-driven communication between cognitive components
- Agent protocol for structured messaging
- Message brokering for agent coordination
"""

from .cognitive_events import CognitiveEventSystem
from .agent_protocol import AgentProtocol
from .message_broker import MessageBroker

__all__ = [
    "CognitiveEventSystem",
    "AgentProtocol",
    "MessageBroker",
]
