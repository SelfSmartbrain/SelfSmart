"""
MCP Discovery - Capability Discovery for Model Context Protocol

Provides unified capability discovery across connected MCP servers,
converting MCP tools to ModelX tool schemas for the tool registry.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from src.tools.mcp_client import MCPClient, MCPTool as MCPClientTool
from src.tools.base import ToolSchema


@dataclass
class MCPServerCapabilities:
    """Capabilities of a single MCP server"""
    server_name: str
    tools: List[Dict[str, Any]]
    resource_templates: List[Dict[str, Any]]
    prompts: List[Dict[str, Any]]


async def discover_mcp_capabilities(client: MCPClient) -> List[ToolSchema]:
    """
    Discover all capabilities across connected MCP servers.
    
    Returns:
        List of ToolSchema objects compatible with ModelX tool registry
    """
    all_tools = []
    
    for server_name, server in client.servers.items():
        if not server.initialized:
            continue
            
        for tool in server.tools:
            all_tools.append(ToolSchema(
                name=f"mcp.{server_name}.{tool.name}",
                description=tool.description,
                parameters=tool.input_schema,
                metadata={
                    "source": "mcp",
                    "server": server_name,
                    "original_name": tool.name,
                }
            ))
    
    return all_tools


async def discover_mcp_resources(client: MCPClient, server_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Discover resource templates from MCP servers.
    
    Args:
        client: MCP client instance
        server_name: Optional specific server to query
        
    Returns:
        List of resource template definitions
    """
    resources = []
    servers = [server_name] if server_name else list(client.servers.keys())
    
    for name in servers:
        server = client.servers.get(name)
        if not server or not server.initialized:
            continue
            
        try:
            response = await client._send_request(name, "resources/list", {})
            if "result" in response:
                for resource in response["result"].get("resources", []):
                    resources.append({
                        "uri": resource.get("uri"),
                        "name": resource.get("name"),
                        "description": resource.get("description"),
                        "mime_type": resource.get("mimeType"),
                        "server": name,
                    })
        except Exception as e:
            # Resource discovery is optional
            pass
    
    return resources


async def discover_mcp_prompts(client: MCPClient, server_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Discover prompt templates from MCP servers.
    
    Args:
        client: MCP client instance
        server_name: Optional specific server to query
        
    Returns:
        List of prompt template definitions
    """
    prompts = []
    servers = [server_name] if server_name else list(client.servers.keys())
    
    for name in servers:
        server = client.servers.get(name)
        if not server or not server.initialized:
            continue
            
        try:
            response = await client._send_request(name, "prompts/list", {})
            if "result" in response:
                for prompt in response["result"].get("prompts", []):
                    prompts.append({
                        "name": prompt.get("name"),
                        "description": prompt.get("description"),
                        "arguments": prompt.get("arguments", []),
                        "server": name,
                    })
        except Exception as e:
            # Prompt discovery is optional
            pass
    
    return prompts


async def get_full_server_capabilities(client: MCPClient, server_name: str) -> Optional[MCPServerCapabilities]:
    """Get complete capabilities for a specific server"""
    server = client.servers.get(server_name)
    if not server or not server.initialized:
        return None
    
    tools = []
    for tool in server.tools:
        tools.append({
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
        })
    
    resources = await discover_mcp_resources(client, server_name)
    prompts = await discover_mcp_prompts(client, server_name)
    
    return MCPServerCapabilities(
        server_name=server_name,
        tools=tools,
        resource_templates=resources,
        prompts=prompts,
    )


async def register_mcp_tools_with_registry(
    client: MCPClient,
    tool_registry: Any,
    server_filter: Optional[List[str]] = None,
) -> int:
    """
    Register all discovered MCP tools with the ModelX tool registry.
    
    Args:
        client: MCP client with connected servers
        tool_registry: ModelX tool registry instance
        server_filter: Optional list of server names to register (None = all)
        
    Returns:
        Number of tools registered
    """
    tools = await discover_mcp_capabilities(client)
    
    if server_filter:
        tools = [t for t in tools if t.metadata.get("server") in server_filter]
    
    registered = 0
    for tool_schema in tools:
        try:
            # Create MCPTool wrapper
            from src.tools.base import MCPTool
            server_name = tool_schema.metadata["server"]
            original_name = tool_schema.metadata["original_name"]
            
            mcp_tool = client.get_tool_schema(server_name, original_name)
            if mcp_tool:
                wrapper = MCPTool.create_from_mcp(client, server_name, mcp_tool)
                tool_registry.register(wrapper)
                registered += 1
        except Exception as e:
            # Log but continue with other tools
            pass
    
    return registered


class MCPCatalogManager:
    """
    Manages a catalog of known MCP server configurations.
    
    Allows easy discovery and connection to standard MCP servers.
    """
    
    # Predefined server configurations (matching mcp_client.py catalog)
    SERVER_CATALOG = {
        "filesystem": {
            "name": "filesystem",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
            "description": "File system operations",
            "env_vars": [],
        },
        "github": {
            "name": "github",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "description": "GitHub API operations",
            "env_vars": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
        },
        "sqlite": {
            "name": "sqlite",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sqlite", "/workspace/data.db"],
            "description": "SQLite database operations",
            "env_vars": [],
        },
        "postgres": {
            "name": "postgres",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-postgres"],
            "description": "PostgreSQL database operations",
            "env_vars": ["POSTGRES_CONNECTION_STRING"],
        },
        "brave-search": {
            "name": "brave-search",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-brave-search"],
            "description": "Web search via Brave",
            "env_vars": ["BRAVE_API_KEY"],
        },
        "fetch": {
            "name": "fetch",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-fetch"],
            "description": "HTTP fetch and web scraping",
            "env_vars": [],
        },
        "git": {
            "name": "git",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-git", "/workspace"],
            "description": "Git repository operations",
            "env_vars": [],
        },
    }
    
    def __init__(self, client: MCPClient):
        self.client = client
    
    def get_available_servers(self) -> Dict[str, Dict[str, Any]]:
        """Get catalog of available server configurations"""
        return self.SERVER_CATALOG.copy()
    
    async def connect_server(self, server_key: str, env_overrides: Optional[Dict[str, str]] = None) -> bool:
        """Connect to a catalog server by key"""
        from src.tools.mcp_client import MCPServerConfig, MCPTransport
        
        config_data = self.SERVER_CATALOG.get(server_key)
        if not config_data:
            raise ValueError(f"Unknown server: {server_key}")
        
        config = MCPServerConfig(
            name=config_data["name"],
            command=config_data["command"],
            args=config_data["args"],
            env=env_overrides or {},
        )
        
        return await self.client.connect_server(config)
    
    async def connect_all(self, env_overrides: Optional[Dict[str, Dict[str, str]]] = None) -> Dict[str, bool]:
        """Connect to all catalog servers"""
        results = {}
        for key in self.SERVER_CATALOG:
            overrides = env_overrides.get(key, {}) if env_overrides else {}
            results[key] = await self.connect_server(key, overrides)
        return results
    
    async def discover_all_tools(self) -> List[ToolSchema]:
        """Discover tools from all connected servers"""
        return await discover_mcp_capabilities(self.client)