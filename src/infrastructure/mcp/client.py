"""MCP Client for connecting to external MCP tool servers.

Supports both stdio and SSE transports. Manages connections to
multiple servers and provides tool discovery and invocation.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from typing import Any, Dict, List, Optional

from utils.log import log_info, log_warning, log_error

from infrastructure.mcp.registry import MCPServerConfig


class MCPToolDefinition:
    """Represents a tool discovered from an MCP server."""

    def __init__(
        self,
        server_id: str,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
    ) -> None:
        self.server_id = server_id
        self.name = name
        self.description = description
        self.input_schema = input_schema

    @property
    def qualified_name(self) -> str:
        """Globally unique tool name: mcp_{server}_{tool}."""
        return f"mcp_{self.server_id}_{self.name}"


class MCPClientManager:
    """Manages connections to multiple MCP servers.

    Lazily initializes connections on first tool list or call.
    Supports both stdio and SSE transports.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, Any] = {}  # server_id -> ClientSession
        self._tools: Dict[str, List[MCPToolDefinition]] = {}  # server_id -> tools
        self._processes: Dict[str, subprocess.Popen] = {}  # server_id -> process

    async def connect(self, config: MCPServerConfig) -> bool:
        """Connect to an MCP server.

        Returns True if connection succeeded.
        """
        if config.id in self._sessions:
            log_warning(f"[MCP] Already connected to '{config.name}'")
            return True

        try:
            if config.transport == "stdio":
                return await self._connect_stdio(config)
            elif config.transport == "sse":
                return await self._connect_sse(config)
            else:
                log_error(f"[MCP] Unknown transport: {config.transport}")
                return False
        except Exception as e:
            log_error(f"[MCP] Failed to connect to '{config.name}': {e}")
            return False

    async def _connect_stdio(self, config: MCPServerConfig) -> bool:
        """Connect via stdio transport (subprocess)."""
        try:
            from mcp import ClientSession
            from mcp.client.stdio import stdio_client, StdioServerParameters

            params = StdioServerParameters(
                command=config.command,
                args=config.args,
                env=config.env or None,
            )

            # Create the stdio connection
            read_stream, write_stream = await stdio_client(params).__aenter__()
            session = ClientSession(read_stream, write_stream)
            await session.__aenter__()
            await session.initialize()

            self._sessions[config.id] = session
            log_info(f"[MCP] Connected to '{config.name}' via stdio")

            # Discover tools
            await self._discover_tools(config.id)
            return True

        except ImportError:
            log_warning("[MCP] mcp package not installed. Run: pip install mcp")
            return False
        except Exception as e:
            log_error(f"[MCP] stdio connection to '{config.name}' failed: {e}")
            return False

    async def _connect_sse(self, config: MCPServerConfig) -> bool:
        """Connect via SSE transport (HTTP)."""
        try:
            from mcp import ClientSession
            from mcp.client.sse import sse_client

            read_stream, write_stream = await sse_client(config.url).__aenter__()
            session = ClientSession(read_stream, write_stream)
            await session.__aenter__()
            await session.initialize()

            self._sessions[config.id] = session
            log_info(f"[MCP] Connected to '{config.name}' via SSE at {config.url}")

            await self._discover_tools(config.id)
            return True

        except ImportError:
            log_warning("[MCP] mcp package not installed. Run: pip install mcp")
            return False
        except Exception as e:
            log_error(f"[MCP] SSE connection to '{config.name}' failed: {e}")
            return False

    async def _discover_tools(self, server_id: str) -> None:
        """Discover available tools from a connected server."""
        session = self._sessions.get(server_id)
        if not session:
            return

        try:
            result = await session.list_tools()
            tools = []
            for tool in result.tools:
                tools.append(MCPToolDefinition(
                    server_id=server_id,
                    name=tool.name,
                    description=tool.description or f"MCP tool: {tool.name}",
                    input_schema=tool.inputSchema if hasattr(tool, "inputSchema") else {},
                ))
            self._tools[server_id] = tools
            log_info(f"[MCP] Discovered {len(tools)} tools from server '{server_id}'")
        except Exception as e:
            log_warning(f"[MCP] Tool discovery failed for '{server_id}': {e}")
            self._tools[server_id] = []

    async def call_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> str:
        """Call a tool on a connected MCP server.

        Returns the tool result as a string.
        """
        session = self._sessions.get(server_id)
        if not session:
            return f"Error: Not connected to server '{server_id}'"

        try:
            result = await session.call_tool(tool_name, arguments)
            # Extract text content from result
            if hasattr(result, "content") and result.content:
                parts = []
                for block in result.content:
                    if hasattr(block, "text"):
                        parts.append(block.text)
                    else:
                        parts.append(str(block))
                return "\n".join(parts)
            return str(result)
        except Exception as e:
            log_error(f"[MCP] Tool call '{tool_name}' on '{server_id}' failed: {e}")
            return f"MCP tool error: {e}"

    def list_tools(self, server_id: Optional[str] = None) -> List[MCPToolDefinition]:
        """List discovered tools, optionally filtered by server."""
        if server_id:
            return self._tools.get(server_id, [])
        all_tools = []
        for tools in self._tools.values():
            all_tools.extend(tools)
        return all_tools

    async def disconnect(self, server_id: str) -> None:
        """Disconnect from an MCP server."""
        session = self._sessions.pop(server_id, None)
        if session:
            try:
                await session.__aexit__(None, None, None)
            except Exception:
                pass
        self._tools.pop(server_id, None)
        log_info(f"[MCP] Disconnected from '{server_id}'")

    async def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        for server_id in list(self._sessions.keys()):
            await self.disconnect(server_id)

    @property
    def connected_servers(self) -> List[str]:
        return list(self._sessions.keys())


# Module-level singleton
_client_manager = MCPClientManager()


def get_mcp_client() -> MCPClientManager:
    return _client_manager
