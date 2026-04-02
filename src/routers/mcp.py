"""MCP server management endpoints.

Provides:
    GET    /mcp/servers         – list configured MCP servers
    POST   /mcp/servers         – add a new MCP server
    DELETE /mcp/servers/{id}    – remove an MCP server
    POST   /mcp/servers/{id}/connect    – connect to a server
    POST   /mcp/servers/{id}/disconnect – disconnect from a server
    GET    /mcp/tools           – list all tools from connected servers
"""

from __future__ import annotations

import asyncio
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from core.dependencies import get_current_user, require_admin
from models.user import User
from utils.log import log_info

router = APIRouter(prefix="/mcp", tags=["mcp"])


class MCPServerCreate(BaseModel):
    id: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    transport: str = Field(..., description="stdio or sse")
    command: Optional[str] = Field(None, description="Command for stdio transport")
    args: List[str] = Field(default_factory=list)
    url: Optional[str] = Field(None, description="URL for SSE transport")
    env: dict = Field(default_factory=dict)
    risk_tier: int = Field(2, ge=1, le=4)


class MCPServerResponse(BaseModel):
    id: str
    name: str
    transport: str
    enabled: bool
    connected: bool
    tool_count: int


class MCPToolResponse(BaseModel):
    server_id: str
    name: str
    qualified_name: str
    description: str


@router.get("/servers", response_model=List[MCPServerResponse])
async def list_servers(
    user: User = Depends(require_admin),
):
    """List all configured MCP servers."""
    from infrastructure.mcp.registry import get_mcp_registry
    from infrastructure.mcp.client import get_mcp_client

    registry = get_mcp_registry()
    client = get_mcp_client()
    connected = set(client.connected_servers)

    result = []
    for server in registry.list_servers():
        tool_count = len(client.list_tools(server.id))
        result.append(MCPServerResponse(
            id=server.id,
            name=server.name,
            transport=server.transport,
            enabled=server.enabled,
            connected=server.id in connected,
            tool_count=tool_count,
        ))
    return result


@router.post("/servers", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def add_server(
    body: MCPServerCreate,
    user: User = Depends(require_admin),
):
    """Add a new MCP server configuration."""
    from infrastructure.mcp.registry import get_mcp_registry, MCPServerConfig

    registry = get_mcp_registry()
    config = MCPServerConfig(
        id=body.id,
        name=body.name,
        transport=body.transport,
        command=body.command,
        args=body.args,
        url=body.url,
        env=body.env,
        risk_tier=body.risk_tier,
    )
    registry.add_server(config)

    return MCPServerResponse(
        id=config.id,
        name=config.name,
        transport=config.transport,
        enabled=config.enabled,
        connected=False,
        tool_count=0,
    )


@router.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_server(
    server_id: str,
    user: User = Depends(require_admin),
):
    """Remove an MCP server and disconnect if connected."""
    from infrastructure.mcp.registry import get_mcp_registry
    from infrastructure.mcp.client import get_mcp_client

    client = get_mcp_client()
    if server_id in client.connected_servers:
        await client.disconnect(server_id)

    registry = get_mcp_registry()
    registry.remove_server(server_id)


@router.post("/servers/{server_id}/connect")
async def connect_server(
    server_id: str,
    user: User = Depends(require_admin),
):
    """Connect to an MCP server and discover its tools."""
    from infrastructure.mcp.registry import get_mcp_registry
    from infrastructure.mcp.client import get_mcp_client

    registry = get_mcp_registry()
    config = registry.get_server(server_id)
    if not config:
        from core.exceptions import NotFoundError
        raise NotFoundError(f"MCP server '{server_id}' not found")

    client = get_mcp_client()
    success = await client.connect(config)

    tools = client.list_tools(server_id)
    return {
        "success": success,
        "server_id": server_id,
        "tools_discovered": len(tools),
        "tool_names": [t.name for t in tools],
    }


@router.post("/servers/{server_id}/disconnect")
async def disconnect_server(
    server_id: str,
    user: User = Depends(require_admin),
):
    """Disconnect from an MCP server."""
    from infrastructure.mcp.client import get_mcp_client

    client = get_mcp_client()
    await client.disconnect(server_id)
    return {"success": True, "server_id": server_id}


@router.get("/tools", response_model=List[MCPToolResponse])
async def list_tools(
    server_id: Optional[str] = None,
    user: User = Depends(require_admin),
):
    """List all discovered tools from connected MCP servers."""
    from infrastructure.mcp.client import get_mcp_client

    client = get_mcp_client()
    tools = client.list_tools(server_id)

    return [
        MCPToolResponse(
            server_id=t.server_id,
            name=t.name,
            qualified_name=t.qualified_name,
            description=t.description,
        )
        for t in tools
    ]
