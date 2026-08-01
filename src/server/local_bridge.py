"""
Native Process Bridge / Local Socket Server for real-time agent communication.

This module exposes a lightweight WebSocket server running on localhost to stream
agent thoughts and receive commands without external FastAPI/REST framework overhead.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Set
from enum import Enum

import websockets
from websockets.server import WebSocketServerProtocol

from src.config.logging import get_logger

logger = get_logger(__name__)


class BridgeEventType(str, Enum):
    """Types of events emitted by the bridge"""
    AGENT_THOUGHT = "agent_thought"
    AGENT_STEP = "agent_step"
    FINE_TUNE_EPOCH = "fine_tune_epoch"
    FINE_TUNE_LOSS = "fine_tune_loss"
    SWARM_STATUS = "swarm_status"
    OBJECTIVE_STARTED = "objective_started"
    OBJECTIVE_COMPLETED = "objective_completed"
    OBJECTIVE_FAILED = "objective_failed"
    CHECKPOINT_CREATED = "checkpoint_created"
    CONSENSUS_REQUEST = "consensus_request"
    CONSENSUS_RESULT = "consensus_result"
    ERROR = "error"


class BridgeCommandType(str, Enum):
    """Types of commands accepted by the bridge"""
    SUBMIT_OBJECTIVE = "submit_objective"
    TRIGGER_FINETUNE = "trigger_finetune"
    PAUSE_HARNESS = "pause_harness"
    RESUME_HARNESS = "resume_harnass"
    SWITCH_MODEL = "switch_model"
    GET_STATUS = "get_status"
    LIST_OBJECTIVES = "list_objectives"
    GET_AGENT_STATE = "get_agent_state"


@dataclass
class BridgeEvent:
    """Event emitted by the bridge to connected clients"""
    event_type: BridgeEventType
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    
    def to_json(self) -> str:
        return json.dumps({
            "event_type": self.event_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
        })


@dataclass
class BridgeCommand:
    """Command received from a client"""
    command_type: BridgeCommandType
    payload: Dict[str, Any]
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_json(cls, json_str: str) -> "BridgeCommand":
        data = json.loads(json_str)
        return cls(
            command_type=BridgeCommandType(data["command_type"]),
            payload=data["payload"],
            request_id=data.get("request_id", str(uuid.uuid4())),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
        )


class ClientConnection:
    """Represents a connected WebSocket client"""
    
    def __init__(self, websocket: WebSocketServerProtocol, client_id: str):
        self.websocket = websocket
        self.client_id = client_id
        self.connected_at = datetime.now()
        self.subscriptions: Set[BridgeEventType] = set()
        self.last_ping = datetime.now()
    
    async def send(self, event: BridgeEvent) -> bool:
        """Send event to client if subscribed"""
        if not self.subscriptions or event.event_type in self.subscriptions:
            try:
                await self.websocket.send(event.to_json())
                return True
            except Exception as exc:
                logger.warning(f"Failed to send to client {self.client_id}: {exc}")
                return False
        return True
    
    async def send_error(self, message: str, request_id: str = None) -> None:
        """Send error response to client"""
        error_event = BridgeEvent(
            event_type=BridgeEventType.ERROR,
            payload={"message": message, "request_id": request_id},
        )
        await self.send(error_event)
    
    async def send_response(self, request_id: str, payload: Dict[str, Any]) -> None:
        """Send command response to client"""
        response_event = BridgeEvent(
            event_type=BridgeEventType.SWARM_STATUS,  # Reuse for responses
            payload={"response": True, "request_id": request_id, **payload},
            correlation_id=request_id,
        )
        await self.send(response_event)


class LocalBridgeServer:
    """
    Lightweight WebSocket server for real-time agent communication.
    
    Runs on localhost:8765 and handles:
    - Streaming agent thoughts, steps, and fine-tune progress
    - Receiving commands from UI/clients
    - Managing client subscriptions
    """
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        ping_interval: float = 20.0,
        ping_timeout: float = 10.0,
    ):
        self.host = host
        self.port = port
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        
        self._server: Optional[websockets.WebSocketServer] = None
        self._clients: Dict[str, ClientConnection] = {}
        self._command_handlers: Dict[BridgeCommandType, Callable] = {}
        self._running = False
        self._broadcast_task: Optional[asyncio.Task] = None
        
        # Register default command handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default command handlers"""
        self._command_handlers = {
            BridgeCommandType.SUBMIT_OBJECTIVE: self._handle_submit_objective,
            BridgeCommandType.TRIGGER_FINETUNE: self._handle_trigger_finetune,
            BridgeCommandType.PAUSE_HARNESS: self._handle_pause_harness,
            BridgeCommandType.RESUME_HARNESS: self._handle_resume_harness,
            BridgeCommandType.SWITCH_MODEL: self._handle_switch_model,
            BridgeCommandType.GET_STATUS: self._handle_get_status,
            BridgeCommandType.LIST_OBJECTIVES: self._handle_list_objectives,
            BridgeCommandType.GET_AGENT_STATE: self._handle_get_agent_state,
        }
    
    def register_command_handler(
        self,
        command_type: BridgeCommandType,
        handler: Callable,
    ) -> None:
        """Register a custom command handler"""
        self._command_handlers[command_type] = handler
    
    async def start(self) -> None:
        """Start the WebSocket server"""
        if self._running:
            logger.warning("Bridge server already running")
            return
        
        self._running = True
        self._server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port,
            ping_interval=self.ping_interval,
            ping_timeout=self.ping_timeout,
        )
        
        # Start broadcast task
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        
        logger.info(f"LocalBridgeServer started on {self.host}:{self.port}")
    
    async def stop(self) -> None:
        """Stop the WebSocket server"""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel broadcast task
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        
        # Close all client connections
        for client in self._clients.values():
            try:
                await client.websocket.close()
            except Exception:
                pass
        
        # Stop server
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        
        self._clients.clear()
        logger.info("LocalBridgeServer stopped")
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol) -> None:
        """Handle new WebSocket connection"""
        client_id = str(uuid.uuid4())
        client = ClientConnection(websocket, client_id)
        self._clients[client_id] = client
        
        logger.info(f"Client connected: {client_id} (total: {len(self._clients)})")
        
        try:
            async for message in websocket:
                await self._handle_message(client, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as exc:
            logger.error(f"Error handling client {client_id}: {exc}")
        finally:
            del self._clients[client_id]
            logger.info(f"Client disconnected: {client_id} (total: {len(self._clients)})")
    
    async def _handle_message(self, client: ClientConnection, message: str) -> None:
        """Handle incoming message from client"""
        try:
            data = json.loads(message)
            
            # Handle subscription requests
            if "subscribe" in data:
                event_types = data["subscribe"]
                if isinstance(event_types, list):
                    for et in event_types:
                        try:
                            client.subscriptions.add(BridgeEventType(et))
                        except ValueError:
                            pass
                return
            
            if "unsubscribe" in data:
                event_types = data["unsubscribe"]
                if isinstance(event_types, list):
                    for et in event_types:
                        try:
                            client.subscriptions.discard(BridgeEventType(et))
                        except ValueError:
                            pass
                return
            
            # Handle commands
            if "command_type" in data:
                command = BridgeCommand.from_json(message)
                await self._handle_command(client, command)
                
        except json.JSONDecodeError:
            await client.send_error("Invalid JSON")
        except Exception as exc:
            logger.error(f"Error handling message from {client.client_id}: {exc}")
            await client.send_error(str(exc))
    
    async def _handle_command(self, client: ClientConnection, command: BridgeCommand) -> None:
        """Handle a command from client"""
        handler = self._command_handlers.get(command.command_type)
        
        if not handler:
            await client.send_error(f"Unknown command: {command.command_type.value}", command.request_id)
            return
        
        try:
            result = await handler(client, command.payload)
            await client.send_response(command.request_id, result or {})
        except Exception as exc:
            logger.error(f"Command {command.command_type.value} failed: {exc}")
            await client.send_error(str(exc), command.request_id)
    
    # Default command handlers (to be overridden by integration)
    async def _handle_submit_objective(self, client: ClientConnection, payload: Dict) -> Dict:
        """Handle submit_objective command"""
        return {"status": "not_implemented", "message": "Integrate with objective manager"}
    
    async def _handle_trigger_finetune(self, client: ClientConnection, payload: Dict) -> Dict:
        """Handle trigger_finetune command"""
        return {"status": "not_implemented", "message": "Integrate with fine-tune pipeline"}
    
    async def _handle_pause_harness(self, client: ClientConnection, payload: Dict) -> Dict:
        """Handle pause_harness command"""
        return {"status": "not_implemented", "message": "Integrate with execution harness"}
    
    async def _handle_resume_harness(self, client: ClientConnection, payload: Dict) -> Dict:
        """Handle resume_harness command"""
        return {"status": "not_implemented", "message": "Integrate with execution harness"}
    
    async def _handle_switch_model(self, client: ClientConnection, payload: Dict) -> Dict:
        """Handle switch_model command"""
        return {"status": "not_implemented", "message": "Integrate with model manager"}
    
    async def _handle_get_status(self, client: ClientConnection, payload: Dict) -> Dict:
        """Handle get_status command"""
        return {
            "status": "running" if self._running else "stopped",
            "connected_clients": len(self._clients),
            "server_uptime_seconds": (datetime.now() - self._started_at).total_seconds() if hasattr(self, '_started_at') else 0,
        }
    
    async def _handle_list_objectives(self, client: ClientConnection, payload: Dict) -> Dict:
        """Handle list_objectives command"""
        return {"objectives": [], "message": "Integrate with objective manager"}
    
    async def _handle_get_agent_state(self, client: ClientConnection, payload: Dict) -> Dict:
        """Handle get_agent_state command"""
        return {"agents": [], "message": "Integrate with agent brain"}
    
    def broadcast(self, event: BridgeEvent) -> None:
        """Broadcast event to all subscribed clients (sync version for non-async contexts)"""
        if not self._running:
            return
        
        # Schedule async broadcast
        asyncio.create_task(self._async_broadcast(event))
    
    async def _async_broadcast(self, event: BridgeEvent) -> None:
        """Async broadcast event to all subscribed clients"""
        if not self._clients:
            return
        
        # Send to all clients that are subscribed
        disconnected = []
        for client_id, client in self._clients.items():
            success = await client.send(event)
            if not success:
                disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            if client_id in self._clients:
                del self._clients[client_id]
    
    async def _broadcast_loop(self) -> None:
        """Background loop for periodic broadcasts (heartbeat, etc.)"""
        while self._running:
            try:
                # Send heartbeat
                heartbeat = BridgeEvent(
                    event_type=BridgeEventType.SWARM_STATUS,
                    payload={"type": "heartbeat", "connected_clients": len(self._clients)},
                )
                await self._async_broadcast(heartbeat)
                
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in broadcast loop: {exc}")
                await asyncio.sleep(30)
    
    @property
    def client_count(self) -> int:
        return len(self._clients)
    
    @property
    def is_running(self) -> bool:
        return self._running


# Convenience function for creating and starting the server
async def create_bridge_server(
    host: str = "127.0.0.1",
    port: int = 8765,
) -> LocalBridgeServer:
    """Create and start a LocalBridgeServer"""
    server = LocalBridgeServer(host=host, port=port)
    await server.start()
    return server