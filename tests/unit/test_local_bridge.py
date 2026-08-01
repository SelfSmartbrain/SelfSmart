"""
Unit tests for LocalBridgeServer - Phase 9: Native Process Bridge / Local Socket Server
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

from src.server.local_bridge import (
    LocalBridgeServer,
    BridgeEventType,
    BridgeCommandType,
    BridgeEvent,
    BridgeCommand,
    ClientConnection,
    create_bridge_server,
)


class TestBridgeEventType:
    """Test BridgeEventType enum"""
    
    def test_event_types(self):
        assert BridgeEventType.AGENT_THOUGHT.value == "agent_thought"
        assert BridgeEventType.AGENT_STEP.value == "agent_step"
        assert BridgeEventType.FINE_TUNE_EPOCH.value == "fine_tune_epoch"
        assert BridgeEventType.FINE_TUNE_LOSS.value == "fine_tune_loss"
        assert BridgeEventType.SWARM_STATUS.value == "swarm_status"
        assert BridgeEventType.OBJECTIVE_STARTED.value == "objective_started"
        assert BridgeEventType.OBJECTIVE_COMPLETED.value == "objective_completed"
        assert BridgeEventType.OBJECTIVE_FAILED.value == "objective_failed"
        assert BridgeEventType.CHECKPOINT_CREATED.value == "checkpoint_created"
        assert BridgeEventType.CONSENSUS_REQUEST.value == "consensus_request"
        assert BridgeEventType.CONSENSUS_RESULT.value == "consensus_result"
        assert BridgeEventType.ERROR.value == "error"


class TestBridgeCommandType:
    """Test BridgeCommandType enum"""
    
    def test_command_types(self):
        assert BridgeCommandType.SUBMIT_OBJECTIVE.value == "submit_objective"
        assert BridgeCommandType.TRIGGER_FINETUNE.value == "trigger_finetune"
        assert BridgeCommandType.PAUSE_HARNESS.value == "pause_harness"
        assert BridgeCommandType.RESUME_HARNESS.value == "resume_harnass"
        assert BridgeCommandType.SWITCH_MODEL.value == "switch_model"
        assert BridgeCommandType.GET_STATUS.value == "get_status"
        assert BridgeCommandType.LIST_OBJECTIVES.value == "list_objectives"
        assert BridgeCommandType.GET_AGENT_STATE.value == "get_agent_state"


class TestBridgeEvent:
    """Test BridgeEvent dataclass"""
    
    def test_event_creation(self):
        event = BridgeEvent(
            event_type=BridgeEventType.AGENT_THOUGHT,
            payload={"agent": "planner", "thought": "Planning..."},
            correlation_id="corr_123",
        )
        
        assert event.event_type == BridgeEventType.AGENT_THOUGHT
        assert event.payload == {"agent": "planner", "thought": "Planning..."}
        assert event.correlation_id == "corr_123"
        assert isinstance(event.timestamp, datetime)
    
    def test_event_to_json(self):
        event = BridgeEvent(
            event_type=BridgeEventType.AGENT_STEP,
            payload={"step": 1, "status": "running"},
        )
        
        json_str = event.to_json()
        data = json.loads(json_str)
        
        assert data["event_type"] == "agent_step"
        assert data["payload"] == {"step": 1, "status": "running"}
        assert "timestamp" in data


class TestBridgeCommand:
    """Test BridgeCommand dataclass"""
    
    def test_command_creation(self):
        command = BridgeCommand(
            command_type=BridgeCommandType.SUBMIT_OBJECTIVE,
            payload={"objective": "Test objective"},
            request_id="req_123",
        )
        
        assert command.command_type == BridgeCommandType.SUBMIT_OBJECTIVE
        assert command.payload == {"objective": "Test objective"}
        assert command.request_id == "req_123"
    
    def test_command_from_json(self):
        json_str = json.dumps({
            "command_type": "trigger_finetune",
            "payload": {"requirement_id": "req_123"},
            "request_id": "req_456",
            "timestamp": "2024-01-01T00:00:00",
        })
        
        command = BridgeCommand.from_json(json_str)
        
        assert command.command_type == BridgeCommandType.TRIGGER_FINETUNE
        assert command.payload == {"requirement_id": "req_123"}
        assert command.request_id == "req_456"


class TestClientConnection:
    """Test ClientConnection"""
    
    @pytest.fixture
    def mock_websocket(self):
        ws = AsyncMock()
        ws.send = AsyncMock()
        ws.close = AsyncMock()
        return ws
    
    @pytest.mark.asyncio
    async def test_send_event_subscribed(self, mock_websocket):
        """Test sending event to subscribed client"""
        client = ClientConnection(mock_websocket, "client_1")
        client.subscriptions.add(BridgeEventType.AGENT_THOUGHT)
        
        event = BridgeEvent(
            event_type=BridgeEventType.AGENT_THOUGHT,
            payload={"test": "data"},
        )
        
        result = await client.send(event)
        
        assert result is True
        mock_websocket.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_event_not_subscribed(self, mock_websocket):
        """Test sending event to non-subscribed client (should still send if no subscriptions)"""
        client = ClientConnection(mock_websocket, "client_1")
        # No subscriptions - should receive all events
        
        event = BridgeEvent(
            event_type=BridgeEventType.AGENT_THOUGHT,
            payload={"test": "data"},
        )
        
        result = await client.send(event)
        
        assert result is True
        mock_websocket.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_event_filtered(self, mock_websocket):
        """Test event filtering by subscription"""
        client = ClientConnection(mock_websocket, "client_1")
        client.subscriptions.add(BridgeEventType.AGENT_STEP)
        # Not subscribed to AGENT_THOUGHT
        
        event = BridgeEvent(
            event_type=BridgeEventType.AGENT_THOUGHT,
            payload={"test": "data"},
        )
        
        result = await client.send(event)
        
        assert result is True  # Returns True but doesn't send
        mock_websocket.send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_error(self, mock_websocket):
        """Test sending error response"""
        client = ClientConnection(mock_websocket, "client_1")
        
        await client.send_error("Test error", "req_123")
        
        mock_websocket.send.assert_called_once()
        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_data["event_type"] == "error"
        assert sent_data["payload"]["message"] == "Test error"
        assert sent_data["payload"]["request_id"] == "req_123"
    
    @pytest.mark.asyncio
    async def test_send_response(self, mock_websocket):
        """Test sending command response"""
        client = ClientConnection(mock_websocket, "client_1")
        
        await client.send_response("req_123", {"status": "ok"})
        
        mock_websocket.send.assert_called_once()
        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        assert sent_data["payload"]["response"] is True
        assert sent_data["payload"]["request_id"] == "req_123"
        assert sent_data["payload"]["status"] == "ok"


class TestLocalBridgeServer:
    """Test LocalBridgeServer"""
    
    @pytest.fixture
    def server(self):
        return LocalBridgeServer(host="127.0.0.1", port=8765)
    
    def test_init(self, server):
        assert server.host == "127.0.0.1"
        assert server.port == 8765
        assert server._running is False
        assert server._server is None
        assert server._clients == {}
        assert len(server._command_handlers) == 8  # 8 default handlers
    
    @pytest.mark.asyncio
    async def test_start_stop(self, server):
        """Test starting and stopping the server"""
        # Create a proper mock that returns an awaitable
        async def mock_serve(*args, **kwargs):
            mock_server = AsyncMock()
            mock_server.close = AsyncMock()
            mock_server.wait_closed = AsyncMock()
            return mock_server
        
        with patch('websockets.serve', side_effect=mock_serve):
            await server.start()
            
            assert server._running is True
            
            await server.stop()
            
            assert server._running is False
    
    @pytest.mark.asyncio
    async def test_start_already_running(self, server):
        """Test starting already running server"""
        server._running = True
        
        with patch('websockets.serve') as mock_serve:
            await server.start()
            mock_serve.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_broadcast_event(self, server):
        """Test broadcasting event"""
        server._running = True
        
        # Create mock clients
        mock_client1 = AsyncMock()
        mock_client1.send = AsyncMock(return_value=True)
        mock_client2 = AsyncMock()
        mock_client2.send = AsyncMock(return_value=True)
        
        server._clients = {
            "client1": mock_client1,
            "client2": mock_client2,
        }
        
        event = BridgeEvent(
            event_type=BridgeEventType.AGENT_THOUGHT,
            payload={"test": "data"},
        )
        
        server.broadcast(event)
        
        # Give time for async broadcast
        await asyncio.sleep(0.1)
        
        mock_client1.send.assert_called_once()
        mock_client2.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_broadcast_filters_by_subscription(self, server):
        """Test broadcast filters by client subscription"""
        server._running = True
        
        # Create actual ClientConnection instances for proper filtering
        mock_ws1 = AsyncMock()
        mock_ws1.send = AsyncMock(return_value=True)
        mock_ws2 = AsyncMock()
        mock_ws2.send = AsyncMock(return_value=True)
        
        client1 = ClientConnection(mock_ws1, "client1")
        client1.subscriptions = {BridgeEventType.AGENT_THOUGHT}
        
        client2 = ClientConnection(mock_ws2, "client2")
        client2.subscriptions = {BridgeEventType.AGENT_STEP}
        
        server._clients = {
            "client1": client1,
            "client2": client2,
        }
        
        event = BridgeEvent(
            event_type=BridgeEventType.AGENT_THOUGHT,
            payload={"test": "data"},
        )
        
        server.broadcast(event)
        await asyncio.sleep(0.1)
        
        mock_ws1.send.assert_called_once()
        mock_ws2.send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_register_command_handler(self, server):
        """Test registering custom command handler"""
        async def custom_handler(client, payload):
            return {"custom": True}
        
        server.register_command_handler(BridgeCommandType.SUBMIT_OBJECTIVE, custom_handler)
        
        assert server._command_handlers[BridgeCommandType.SUBMIT_OBJECTIVE] == custom_handler
    
    @pytest.mark.asyncio
    async def test_client_count(self, server):
        """Test client count property"""
        assert server.client_count == 0
        
        server._clients = {"client1": Mock(), "client2": Mock()}
        assert server.client_count == 2
    
    @pytest.mark.asyncio
    async def test_is_running(self, server):
        """Test is_running property"""
        assert server.is_running is False
        
        server._running = True
        assert server.is_running is True


class TestCreateBridgeServer:
    """Test create_bridge_server factory function"""
    
    @pytest.mark.asyncio
    async def test_create_bridge_server(self):
        """Test factory function creates and starts server"""
        with patch('src.server.local_bridge.LocalBridgeServer') as mock_server_class:
            mock_server = AsyncMock()
            mock_server.start = AsyncMock()
            mock_server_class.return_value = mock_server
            
            server = await create_bridge_server("127.0.0.1", 8765)
            
            assert server == mock_server
            mock_server_class.assert_called_once_with(host="127.0.0.1", port=8765)
            mock_server.start.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])