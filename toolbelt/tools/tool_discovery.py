"""ToolDiscoveryTool - Dynamic tool discovery for Stack 3.0"""

import json
from datetime import datetime
from typing import Any, Dict, List

from .base import BaseTool, ToolResult
from .registry import tool_registry


class ToolSearchTool(BaseTool):
    """Search for tools by capability or keyword."""

    name = "tool_search"
    description = "Search available tools by keyword or capability"

    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (tool name, capability, or keyword)"
            },
            "capability": {
                "type": "string",
                "description": "Filter by capability (web, task, agent, data, etc.)"
            }
        },
        "required": ["query"]
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Search tools."""
        query = input_data.get("query")
        if not query:
            return ToolResult(success=False, error="Missing required parameter: query")

        capability = input_data.get("capability")
        all_tools = tool_registry.list_tools()
        query_lower = query.lower()

        matches = []
        for name, tool_info in all_tools.items():
            desc = tool_info.get("description", "").lower()
            if query_lower in name.lower() or query_lower in desc:
                matches.append({"name": name, **tool_info})

        if capability:
            cap_lower = capability.lower()
            matches = [m for m in matches if cap_lower in m.get("description", "").lower()]

        return ToolResult(success=True, data={
            "query": query,
            "capability": capability,
            "matches": matches,
            "count": len(matches)
        })


class ToolListAllTool(BaseTool):
    """List all registered tools."""

    name = "tool_list_all"
    description = "List all available tools in the registry"

    input_schema = {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Filter by category (web, task, agent, team, skill, etc.)"
            }
        },
        "required": []
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """List all tools."""
        category = input_data.get("category")
        all_tools = tool_registry.list_tools()

        if category:
            cat_lower = category.lower()
            filtered = {k: v for k, v in all_tools.items() if cat_lower in v.get("description", "").lower()}
            return ToolResult(success=True, data={
                "category": category,
                "tools": filtered,
                "count": len(filtered)
            })

        return ToolResult(success=True, data={
            "tools": all_tools,
            "count": len(all_tools)
        })


class ToolInfoTool(BaseTool):
    """Get detailed information about a specific tool."""

    name = "tool_info"
    description = "Get detailed information about a specific tool"

    input_schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Tool name"
            }
        },
        "required": ["name"]
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Get tool info."""
        name = input_data.get("name")
        if not name:
            return ToolResult(success=False, error="Missing required parameter: name")

        tool = tool_registry.get(name)

        if not tool:
            return ToolResult(success=False, error=f"Tool '{name}' not found")

        return ToolResult(success=True, data={
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema
        })


class ToolCapabilitiesTool(BaseTool):
    """List all available capabilities/functionalities."""

    name = "tool_capabilities"
    description = "List all tool capabilities grouped by category"

    input_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """List capabilities."""
        all_tools = tool_registry.list_tools()

        categories = {
            "web": ["web_search", "web_fetch", "web_fetch_meta"],
            "task": ["task_create", "task_list", "task_update", "task_delete"],
            "agent": ["agent_spawn", "agent_status", "agent_list"],
            "team": ["team_create", "team_disband", "team_list", "team_status", "team_assign"],
            "skill": ["skill_list", "skill_execute", "skill_info", "skill_chain", "skill_search"],
            "scheduling": ["cron_create", "cron_list", "cron_delete"],
            "messaging": ["message_send", "message_list", "message_channel", "message_template"],
            "remote": ["remote_add", "remote_list", "remote_trigger", "remote_remove"],
            "discovery": ["tool_search", "tool_list_all", "tool_info", "tool_capabilities"]
        }

        capabilities = {}
        for cat, tools in categories.items():
            available = [t for t in tools if t in all_tools]
            if available:
                capabilities[cat] = available

        return ToolResult(success=True, data={
            "capabilities": capabilities,
            "total_categories": len(capabilities)
        })


from typing import Optional
from .base import BaseTool

# Register tools
tool_registry.register(ToolSearchTool())
tool_registry.register(ToolListAllTool())
tool_registry.register(ToolInfoTool())
tool_registry.register(ToolCapabilitiesTool())
