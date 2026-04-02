"""Adapts MCP tool definitions into LangChain @tool functions.

Converts MCP tools into callable LangChain tools that the existing
planner/agent architecture can use transparently alongside native tools.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

from langchain_core.tools import tool as lc_tool, StructuredTool
from pydantic import BaseModel, Field, create_model

from infrastructure.mcp.client import MCPClientManager, MCPToolDefinition, get_mcp_client
from infrastructure.mcp.registry import get_mcp_registry
from workflows.tool_registry import ToolRegistryEntry
from utils.log import log_info, log_warning


def _json_schema_to_pydantic_fields(
    schema: Dict[str, Any],
) -> Dict[str, Any]:
    """Convert JSON Schema properties to Pydantic field definitions.

    Returns a dict suitable for create_model(**fields).
    """
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    fields = {}

    type_map = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    for name, prop in props.items():
        py_type = type_map.get(prop.get("type", "string"), str)
        description = prop.get("description", "")
        default = ... if name in required else None

        if name in required:
            fields[name] = (py_type, Field(description=description))
        else:
            fields[name] = (py_type, Field(default=default, description=description))

    return fields


def mcp_tool_to_langchain(
    tool_def: MCPToolDefinition,
    client: MCPClientManager,
) -> StructuredTool:
    """Convert an MCP tool definition into a LangChain StructuredTool.

    The returned tool calls the MCP server when invoked by the agent.
    """
    # Build a Pydantic model for the tool's input schema
    fields = _json_schema_to_pydantic_fields(tool_def.input_schema)

    if fields:
        InputModel = create_model(
            f"MCP_{tool_def.server_id}_{tool_def.name}_Input",
            **fields,
        )
    else:
        InputModel = create_model(
            f"MCP_{tool_def.server_id}_{tool_def.name}_Input",
            query=(str, Field(default="", description="Input query")),
        )

    server_id = tool_def.server_id
    tool_name = tool_def.name

    def _invoke_mcp(**kwargs) -> str:
        """Synchronous wrapper around async MCP tool call."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        client.call_tool(server_id, tool_name, kwargs),
                    )
                    return future.result(timeout=30)
            else:
                return asyncio.run(
                    client.call_tool(server_id, tool_name, kwargs)
                )
        except Exception as e:
            return f"MCP tool error: {e}"

    return StructuredTool.from_function(
        func=_invoke_mcp,
        name=tool_def.qualified_name,
        description=tool_def.description,
        args_schema=InputModel,
    )


def get_mcp_langchain_tools() -> List[StructuredTool]:
    """Get all MCP tools as LangChain StructuredTools.

    Called by the tool builder to include MCP tools alongside native tools.
    """
    client = get_mcp_client()
    all_tools = client.list_tools()

    lc_tools = []
    for tool_def in all_tools:
        try:
            lc_tool = mcp_tool_to_langchain(tool_def, client)
            lc_tools.append(lc_tool)
        except Exception as e:
            log_warning(f"[MCP] Failed to adapt tool '{tool_def.name}': {e}")

    if lc_tools:
        log_info(f"[MCP] Adapted {len(lc_tools)} MCP tools to LangChain format")

    return lc_tools


def get_mcp_registry_entries() -> Dict[str, ToolRegistryEntry]:
    """Get MCP tools as ToolRegistryEntry objects for the planner.

    Returns entries that can be merged into the tool registry so the
    planner can discover and route to MCP tools.
    """
    client = get_mcp_client()
    all_tools = client.list_tools()

    entries = {}
    for tool_def in all_tools:
        entries[tool_def.qualified_name] = ToolRegistryEntry(
            name=tool_def.qualified_name,
            description=f"[MCP:{tool_def.server_id}] {tool_def.description}",
            guide=(
                f"## Tool: {tool_def.qualified_name}\n\n"
                f"MCP tool from server '{tool_def.server_id}'.\n"
                f"{tool_def.description}\n\n"
                f"Input schema: {json.dumps(tool_def.input_schema, indent=2)}"
            ),
        )

    return entries
