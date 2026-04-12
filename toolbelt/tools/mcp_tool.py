"""MCPTool - MCP protocol tool integration for Stack 3.0"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .base import BaseTool, ToolResult
from .registry import tool_registry

MCP_CONFIG_FILE = Path.home() / ".stack-3.0" / "mcp_config.json"


def _load_mcp_config() -> Dict[str, Any]:
    """Load MCP configuration."""
    MCP_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if MCP_CONFIG_FILE.exists():
        return json.loads(MCP_CONFIG_FILE.read_text())
    return {"servers": {}}


class MCPTool(BaseTool):
    """Call an MCP server tool."""

    name = "mcp_call"
    description = "Call a tool on an MCP server"

    input_schema = {
        "type": "object",
        "properties": {
            "server_name": {"type": "string", "description": "MCP server name"},
            "tool_name": {"type": "string", "description": "Tool to call on server"},
            "args": {"type": "object", "description": "Arguments for the tool"}
        },
        "required": ["server_name", "tool_name"]
    }

    async def execute(self, server_name: str, tool_name: str, args: Optional[Dict] = None) -> ToolResult:
        """Call MCP tool."""
        config = _load_mcp_config()

        if server_name not in config.get("servers", {}):
            return ToolResult(success=False, error=f"MCP server '{server_name}' not configured")

        server = config["servers"][server_name]

        return ToolResult(success=True, data={
            "server": server_name,
            "tool": tool_name,
            "arguments": args or {},
            "status": "simulated",
            "note": f"MCP call to {server_name}/{tool_name} - requires MCP runtime"
        })


class MCPServerListTool(BaseTool):
    """List configured MCP servers."""

    name = "mcp_list_servers"
    description = "List all configured MCP servers"

    input_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }

    async def execute(self) -> ToolResult:
        """List MCP servers."""
        config = _load_mcp_config()
        servers = config.get("servers", {})

        return ToolResult(success=True, data={
            "servers": list(servers.keys()),
            "count": len(servers)
        })


class MCPServerAddTool(BaseTool):
    """Add an MCP server configuration."""

    name = "mcp_add_server"
    description = "Add an MCP server configuration"

    input_schema = {
        "type": "object",
        "properties": {
            "server_name": {"type": "string", "description": "Server name"},
            "command": {"type": "string", "description": "Command to start server"},
            "args": {"type": "array", "items": {"type": "string"}, "description": "Command arguments"},
            "env": {"type": "object", "description": "Environment variables"}
        },
        "required": ["server_name", "command"]
    }

    async def execute(self, server_name: str, command: str, args: Optional[list] = None, env: Optional[Dict] = None) -> ToolResult:
        """Add MCP server."""
        config = _load_mcp_config()

        if "servers" not in config:
            config["servers"] = {}

        config["servers"][server_name] = {
            "command": command,
            "args": args or [],
            "env": env or {},
            "enabled": True
        }

        MCP_CONFIG_FILE.write_text(json.dumps(config, indent=2))

        return ToolResult(success=True, data={
            "server": server_name,
            "status": "added"
        })


class ReadMcpResourceTool(BaseTool):
    """Read a resource from an MCP server."""

    name = "read_mcp_resource"
    description = "Read a resource from an MCP server"

    input_schema = {
        "type": "object",
        "properties": {
            "server_name": {"type": "string", "description": "MCP server name"},
            "resource_uri": {"type": "string", "description": "Resource URI"}
        },
        "required": ["server_name", "resource_uri"]
    }

    async def execute(self, server_name: str, resource_uri: str) -> ToolResult:
        """Read MCP resource."""
        config = _load_mcp_config()

        if server_name not in config.get("servers", {}):
            return ToolResult(success=False, error=f"MCP server '{server_name}' not configured")

        return ToolResult(success=True, data={
            "server": server_name,
            "resource_uri": resource_uri,
            "status": "simulated",
            "note": f"Read resource {resource_uri} from {server_name}"
        })


# Register tools
tool_registry.register(MCPTool())
tool_registry.register(MCPServerListTool())
tool_registry.register(MCPServerAddTool())
tool_registry.register(ReadMcpResourceTool())
