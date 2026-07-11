"""
MCP Client - Model Context Protocol Integration

Provides standardized tool discovery and invocation via MCP servers.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import shlex

logger = logging.getLogger(__name__)


class MCPTransport(Enum):
    """MCP transport types"""
    STDIO = "stdio"
    SSE = "sse"
    WEBSOCKET = "websocket"


@dataclass
class MCPTool:
    """MCP tool definition"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str = ""


@dataclass
class MCPServerConfig:
    """MCP server configuration"""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    transport: MCPTransport = MCPTransport.STDIO
    timeout: int = 30
    description: str = ""


@dataclass
class MCPServer:
    """Running MCP server instance"""
    config: MCPServerConfig
    process: Optional[asyncio.subprocess.Process] = None
    tools: List[MCPTool] = field(default_factory=list)
    initialized: bool = False
    last_ping: float = 0.0


class MCPClient:
    """
    Client for Model Context Protocol servers.
    
    Manages server lifecycle, tool discovery, and invocation.
    Supports stdio transport for local MCP servers.
    """

    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self._request_handlers: Dict[str, asyncio.Future] = {}
        self._notification_handlers: List[Callable] = []

    async def connect_server(self, config: MCPServerConfig) -> bool:
        """
        Connect to an MCP server.
        
        Args:
            config: Server configuration
            
        Returns:
            True if connected successfully
        """
        if config.name in self.servers:
            logger.warning(f"Server {config.name} already connected")
            return False

        logger.info(f"Connecting to MCP server: {config.name}")

        try:
            if config.transport == MCPTransport.STDIO:
                await self._connect_stdio(config)
            else:
                raise NotImplementedError(f"Transport {config.transport} not yet implemented")

            # Initialize and discover tools
            await self._initialize_server(config.name)
            await self._discover_tools(config.name)

            logger.info(f"MCP server {config.name} connected with {len(self.servers[config.name].tools)} tools")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to MCP server {config.name}: {e}")
            await self._cleanup_server(config.name)
            return False

    async def _connect_stdio(self, config: MCPServerConfig) -> None:
        """Connect via stdio transport"""
        # Prepare command
        cmd = [config.command] + config.args
        env = {**config.env} if config.env else None

        # Start process
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        server = MCPServer(config=config, process=process)
        self.servers[config.name] = server

        # Start stdout reader
        asyncio.create_task(self._read_stdout(config.name))

        # Start stderr reader for logging
        asyncio.create_task(self._read_stderr(config.name))

    async def _read_stdout(self, server_name: str) -> None:
        """Read responses from server stdout"""
        server = self.servers.get(server_name)
        if not server or not server.process:
            return

        while True:
            try:
                line = await server.process.stdout.readline()
                if not line:
                    break

                line = line.decode().strip()
                if not line:
                    continue

                logger.debug(f"MCP [{server_name}] <- {line}")
                await self._handle_message(server_name, line)

            except Exception as e:
                logger.error(f"Error reading from MCP server {server_name}: {e}")
                break

    async def _read_stderr(self, server_name: str) -> None:
        """Read stderr for logging"""
        server = self.servers.get(server_name)
        if not server or not server.process:
            return

        while True:
            try:
                line = await server.process.stderr.readline()
                if not line:
                    break
                logger.debug(f"MCP [{server_name}] stderr: {line.decode().strip()}")
            except Exception:
                break

    async def _handle_message(self, server_name: str, message: str) -> None:
        """Handle incoming MCP message"""
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from {server_name}: {message}")
            return

        # Handle response to request
        if "id" in data and data["id"] in self._request_handlers:
            future = self._request_handlers.pop(data["id"])
            if not future.done():
                future.set_result(data)
            return

        # Handle notification
        if "method" in data and data["method"].startswith("notifications/"):
            for handler in self._notification_handlers:
                try:
                    await handler(server_name, data)
                except Exception as e:
                    logger.error(f"Notification handler error: {e}")
            return

        logger.debug(f"Unhandled MCP message from {server_name}: {data}")

    async def _send_request(self, server_name: str, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON-RPC request and wait for response"""
        server = self.servers.get(server_name)
        if not server or not server.process:
            raise RuntimeError(f"Server {server_name} not connected")

        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        future = asyncio.get_event_loop().create_future()
        self._request_handlers[request_id] = future

        try:
            message = json.dumps(request) + "\n"
            server.process.stdin.write(message.encode())
            await server.process.stdin.drain()
            logger.debug(f"MCP [{server_name}] -> {message.strip()}")

            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=server.config.timeout)
            return response

        except asyncio.TimeoutError:
            self._request_handlers.pop(request_id, None)
            raise RuntimeError(f"MCP request timeout: {method}")
        except Exception as e:
            self._request_handlers.pop(request_id, None)
            raise

    async def _initialize_server(self, server_name: str) -> None:
        """Initialize MCP server connection"""
        response = await self._send_request(server_name, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
            },
            "clientInfo": {
                "name": "ModelX",
                "version": "1.0.0",
            },
        })

        if "error" in response:
            raise RuntimeError(f"MCP initialize failed: {response['error']}")

        self.servers[server_name].initialized = True
        logger.info(f"MCP server {server_name} initialized")

    async def _discover_tools(self, server_name: str) -> None:
        """Discover available tools from server"""
        response = await self._send_request(server_name, "tools/list", {})

        if "error" in response:
            raise RuntimeError(f"MCP tools/list failed: {response['error']}")

        tools = []
        for tool_data in response.get("result", {}).get("tools", []):
            tools.append(MCPTool(
                name=tool_data["name"],
                description=tool_data.get("description", ""),
                input_schema=tool_data.get("inputSchema", {}),
                server_name=server_name,
            ))

        self.servers[server_name].tools = tools
        logger.info(f"Discovered {len(tools)} tools from {server_name}")

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """
        Call a tool on an MCP server.
        
        Args:
            server_name: Name of connected server
            tool_name: Tool to call
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        server = self.servers.get(server_name)
        if not server:
            raise RuntimeError(f"Server {server_name} not connected")

        if not server.initialized:
            raise RuntimeError(f"Server {server_name} not initialized")

        # Verify tool exists
        tool = next((t for t in server.tools if t.name == tool_name), None)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found on server {server_name}")

        response = await self._send_request(server_name, "tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })

        if "error" in response:
            raise RuntimeError(f"MCP tool call failed: {response['error']}")

        return response.get("result", {})

    async def list_tools(self, server_name: Optional[str] = None) -> List[MCPTool]:
        """List all available tools, optionally filtered by server"""
        all_tools = []
        servers = [server_name] if server_name else list(self.servers.keys())
        
        for name in servers:
            server = self.servers.get(name)
            if server:
                all_tools.extend(server.tools)
        
        return all_tools

    async def get_tool_schema(self, server_name: str, tool_name: str) -> Optional[MCPTool]:
        """Get tool schema by name"""
        server = self.servers.get(server_name)
        if not server:
            return None
        return next((t for t in server.tools if t.name == tool_name), None)

    def register_notification_handler(self, handler: Callable) -> None:
        """Register handler for server notifications"""
        self._notification_handlers.append(handler)

    async def disconnect_server(self, server_name: str) -> bool:
        """Disconnect from an MCP server"""
        server = self.servers.get(server_name)
        if not server:
            return False

        await self._cleanup_server(server_name)
        return True

    async def _cleanup_server(self, server_name: str) -> None:
        """Clean up server resources"""
        server = self.servers.pop(server_name, None)
        if not server:
            return

        if server.process:
            try:
                server.process.terminate()
                await asyncio.wait_for(server.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                server.process.kill()
                await server.process.wait()
            except Exception as e:
                logger.error(f"Error cleaning up server {server_name}: {e}")

        logger.info(f"MCP server {server_name} disconnected")

    async def disconnect_all(self) -> None:
        """Disconnect from all servers"""
        for name in list(self.servers.keys()):
            await self.disconnect_server(name)

    def get_server_status(self, server_name: str) -> Dict[str, Any]:
        """Get server connection status"""
        server = self.servers.get(server_name)
        if not server:
            return {"connected": False}

        return {
            "connected": True,
            "initialized": server.initialized,
            "tool_count": len(server.tools),
            "transport": server.config.transport.value,
        }


class MCPToolWrapper:
    """
    Wrapper to make MCP tools compatible with ModelX tool interface.
    """

    def __init__(self, mcp_client: MCPClient, server_name: str, tool: MCPTool):
        self.client = mcp_client
        self.server_name = server_name
        self.tool = tool
        self.name = f"mcp.{server_name}.{tool.name}"
        self.description = tool.description
        self.parameters = tool.input_schema

    async def execute(self, **kwargs) -> Any:
        """Execute the MCP tool"""
        return await self.client.call_tool(self.server_name, self.tool.name, kwargs)

    def to_tool_schema(self) -> Dict[str, Any]:
        """Convert to ModelX tool schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


async def discover_mcp_capabilities(client: MCPClient) -> List[Dict[str, Any]]:
    """
    Discover all capabilities across connected MCP servers.
    
    Returns:
        List of tool schemas compatible with ModelX tool registry
    """
    all_tools = []
    
    for server_name, server in client.servers.items():
        for tool in server.tools:
            wrapper = MCPToolWrapper(client, server_name, tool)
            all_tools.append(wrapper.to_tool_schema())
    
    return all_tools


# Predefined MCP server configurations for common tools
MCP_SERVER_CATALOG = {
    "filesystem": MCPServerConfig(
        name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
        description="File system operations",
    ),
    "github": MCPServerConfig(
        name="github",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"},
        description="GitHub API operations",
    ),
    "sqlite": MCPServerConfig(
        name="sqlite",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-sqlite", "/workspace/data.db"],
        description="SQLite database operations",
    ),
    "postgres": MCPServerConfig(
        name="postgres",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-postgres"],
        env={"POSTGRES_CONNECTION_STRING": "${DATABASE_URL}"},
        description="PostgreSQL database operations",
    ),
    "brave-search": MCPServerConfig(
        name="brave-search",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-brave-search"],
        env={"BRAVE_API_KEY": "${BRAVE_API_KEY}"},
        description="Web search via Brave",
    ),
    "fetch": MCPServerConfig(
        name="fetch",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-fetch"],
        description="HTTP fetch and web scraping",
    ),
    "git": MCPServerConfig(
        name="git",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-git", "/workspace"],
        description="Git repository operations",
    ),
}