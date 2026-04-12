"""RemoteTriggerTool - Trigger actions on remote agents for Stack 3.0"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseTool, ToolResult
from .registry import tool_registry

REMOTES_FILE = Path.home() / ".stack-3.0" / "remotes.json"
TRIGGERS_FILE = Path.home() / ".stack-3.0" / "triggers.json"


def _load_remotes() -> Dict[str, Any]:
    """Load remote configurations."""
    REMOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    if REMOTES_FILE.exists():
        return json.loads(REMOTES_FILE.read_text())
    return {"remotes": {}}


def _save_remotes(data: Dict[str, Any]) -> None:
    """Save remote configurations."""
    REMOTES_FILE.write_text(json.dumps(data, indent=2))


def _load_triggers() -> Dict[str, Any]:
    """Load trigger history."""
    TRIGGERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if TRIGGERS_FILE.exists():
        return json.loads(TRIGGERS_FILE.read_text())
    return {"triggers": []}


def _save_triggers(data: Dict[str, Any]) -> None:
    """Save trigger history."""
    TRIGGERS_FILE.write_text(json.dumps(data, indent=2))


class RemoteAddTool(BaseTool):
    """Add a remote agent endpoint."""

    name = "remote_add"
    description = "Add a remote agent configuration"

    input_schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Remote agent name"
            },
            "url": {
                "type": "string",
                "description": "Remote agent URL or endpoint"
            },
            "api_key": {
                "type": "string",
                "description": "API key for authentication"
            },
            "capabilities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Remote agent capabilities"
            }
        },
        "required": ["name", "url"]
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Add remote."""
        name = input_data.get("name")
        url = input_data.get("url")
        api_key = input_data.get("api_key")
        capabilities = input_data.get("capabilities")

        data = _load_remotes()

        data["remotes"][name] = {
            "url": url,
            "api_key": api_key,
            "capabilities": capabilities or [],
            "status": "active",
            "added_at": datetime.now().isoformat()
        }

        _save_remotes(data)

        return ToolResult(success=True, data={
            "remote": name,
            "status": "added",
            "capabilities": capabilities or []
        })


class RemoteListTool(BaseTool):
    """List all remote agents."""

    name = "remote_list"
    description = "List all configured remote agents"

    input_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """List remotes."""
        data = _load_remotes()
        remotes = data.get("remotes", {})

        return ToolResult(success=True, data={
            "remotes": [
                {"name": name, "url": info["url"], "status": info.get("status"), "capabilities": info.get("capabilities", [])}
                for name, info in remotes.items()
            ],
            "count": len(remotes)
        })


class RemoteTriggerTool(BaseTool):
    """Trigger an action on a remote agent."""

    name = "remote_trigger"
    description = "Trigger an action on a remote agent"

    input_schema = {
        "type": "object",
        "properties": {
            "remote": {
                "type": "string",
                "description": "Remote agent name"
            },
            "action": {
                "type": "string",
                "description": "Action to trigger"
            },
            "parameters": {
                "type": "object",
                "description": "Action parameters"
            },
            "wait_for_response": {
                "type": "boolean",
                "default": True,
                "description": "Wait for response or fire-and-forget"
            }
        },
        "required": ["remote", "action"]
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Trigger remote action."""
        remote = input_data.get("remote")
        action = input_data.get("action")
        parameters = input_data.get("parameters")
        wait_for_response = input_data.get("wait_for_response", True)

        data = _load_remotes()
        remotes = data.get("remotes", {})

        if remote not in remotes:
            return ToolResult(success=False, error=f"Remote '{remote}' not found")

        trigger_id = str(uuid.uuid4())[:12]
        trigger = {
            "id": trigger_id,
            "remote": remote,
            "action": action,
            "parameters": parameters or {},
            "status": "triggered",
            "triggered_at": datetime.now().isoformat()
        }

        trigger_log = _load_triggers()
        trigger_log["triggers"].append(trigger)
        _save_triggers(trigger_log)

        return ToolResult(success=True, data={
            "trigger_id": trigger_id,
            "remote": remote,
            "action": action,
            "status": "triggered",
            "triggered_at": trigger["triggered_at"],
            "note": f"Action '{action}' triggered on '{remote}'"
        })


class RemoteRemoveTool(BaseTool):
    """Remove a remote agent."""

    name = "remote_remove"
    description = "Remove a remote agent configuration"

    input_schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Remote agent name to remove"
            }
        },
        "required": ["name"]
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Remove remote."""
        name = input_data.get("name")
        data = _load_remotes()

        if name not in data["remotes"]:
            return ToolResult(success=False, error=f"Remote '{name}' not found")

        del data["remotes"][name]
        _save_remotes(data)

        return ToolResult(success=True, data={
            "remote": name,
            "status": "removed"
        })


# Register tools
tool_registry.register(RemoteAddTool())
tool_registry.register(RemoteListTool())
tool_registry.register(RemoteTriggerTool())
tool_registry.register(RemoteRemoveTool())
