"""MCP server configuration registry.

Manages which MCP servers are available, their connection parameters,
and persistence of server configs in the database or settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

from utils.log import log_info, log_warning


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server connection."""

    id: str
    name: str
    transport: Literal["stdio", "sse"]
    enabled: bool = True

    # stdio transport
    command: Optional[str] = None
    args: list[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)

    # SSE transport
    url: Optional[str] = None

    # Safety
    risk_tier: int = 2  # Default: soft confirm


class MCPServerRegistry:
    """In-memory registry of MCP server configurations.

    Servers can be added/removed at runtime. The registry does NOT
    manage connections — that's the client's job.
    """

    def __init__(self) -> None:
        self._servers: Dict[str, MCPServerConfig] = {}

    def add_server(self, config: MCPServerConfig) -> None:
        self._servers[config.id] = config
        log_info(f"[MCP Registry] Added server '{config.name}' (id={config.id}, transport={config.transport})")

    def remove_server(self, server_id: str) -> bool:
        if server_id in self._servers:
            del self._servers[server_id]
            log_info(f"[MCP Registry] Removed server '{server_id}'")
            return True
        return False

    def get_server(self, server_id: str) -> Optional[MCPServerConfig]:
        return self._servers.get(server_id)

    def list_servers(self, enabled_only: bool = False) -> List[MCPServerConfig]:
        servers = list(self._servers.values())
        if enabled_only:
            servers = [s for s in servers if s.enabled]
        return servers

    def enable_server(self, server_id: str) -> bool:
        server = self._servers.get(server_id)
        if server:
            server.enabled = True
            return True
        return False

    def disable_server(self, server_id: str) -> bool:
        server = self._servers.get(server_id)
        if server:
            server.enabled = False
            return True
        return False


# Module-level singleton
_registry = MCPServerRegistry()


def get_mcp_registry() -> MCPServerRegistry:
    return _registry
