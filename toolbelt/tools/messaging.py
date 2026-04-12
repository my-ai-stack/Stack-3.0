"""SendMessageTool - Structured messaging between agents/users for Stack 3.0"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseTool, ToolResult
from .registry import tool_registry

MESSAGES_FILE = Path.home() / ".stack-3.0" / "messages.json"


def _load_messages() -> Dict[str, Any]:
    """Load messages from disk."""
    MESSAGES_FILE.parent.mkdir(parents=True, exist_ok=True)
    if MESSAGES_FILE.exists():
        return json.loads(MESSAGES_FILE.read_text())
    return {"messages": [], "channels": {}}


def _save_messages(data: Dict[str, Any]) -> None:
    """Save messages to disk."""
    MESSAGES_FILE.write_text(json.dumps(data, indent=2))


class MessageSendTool(BaseTool):
    """Send a structured message to a recipient or channel."""

    name = "message_send"
    description = "Send a message to a user, agent, or channel"

    input_schema = {
        "type": "object",
        "properties": {
            "recipient": {
                "type": "string",
                "description": "Recipient user, agent, or channel name"
            },
            "content": {
                "type": "string",
                "description": "Message content"
            },
            "channel": {
                "type": "string",
                "default": "default",
                "description": "Channel to send to"
            },
            "priority": {
                "type": "string",
                "enum": ["low", "normal", "high", "urgent"],
                "default": "normal"
            },
            "template": {
                "type": "string",
                "description": "Optional message template name"
            }
        },
        "required": ["recipient", "content"]
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Send a message."""
        recipient = input_data.get("recipient")
        content = input_data.get("content")
        channel = input_data.get("channel", "default")
        priority = input_data.get("priority", "normal")
        template = input_data.get("template")

        data = _load_messages()

        msg_id = str(uuid.uuid4())[:12]
        message = {
            "id": msg_id,
            "recipient": recipient,
            "content": content,
            "channel": channel,
            "priority": priority,
            "template": template,
            "status": "sent",
            "sent_at": datetime.now().isoformat()
        }

        data["messages"].append(message)

        if channel not in data["channels"]:
            data["channels"][channel] = []
        data["channels"][channel].append(msg_id)

        _save_messages(data)

        return ToolResult(success=True, data={
            "message_id": msg_id,
            "recipient": recipient,
            "channel": channel,
            "status": "sent",
            "sent_at": message["sent_at"]
        })


class MessageListTool(BaseTool):
    """List messages, optionally filtered."""

    name = "message_list"
    description = "List messages with optional filters"

    input_schema = {
        "type": "object",
        "properties": {
            "channel": {
                "type": "string",
                "description": "Filter by channel"
            },
            "recipient": {
                "type": "string",
                "description": "Filter by recipient"
            },
            "limit": {
                "type": "number",
                "default": 50,
                "description": "Maximum messages to return"
            }
        },
        "required": []
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """List messages."""
        channel = input_data.get("channel")
        recipient = input_data.get("recipient")
        limit = input_data.get("limit", 50)

        data = _load_messages()
        messages = data.get("messages", [])

        if channel:
            messages = [m for m in messages if m.get("channel") == channel]
        if recipient:
            messages = [m for m in messages if m.get("recipient") == recipient]

        messages = messages[-limit:]

        return ToolResult(success=True, data={
            "messages": messages,
            "count": len(messages)
        })


class MessageChannelTool(BaseTool):
    """Manage message channels."""

    name = "message_channel"
    description = "Create, list, or manage message channels"

    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "list", "info"],
                "description": "Action to perform"
            },
            "name": {
                "type": "string",
                "description": "Channel name (for create/info)"
            },
            "description": {
                "type": "string",
                "description": "Channel description (for create)"
            }
        },
        "required": ["action"]
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Manage channels."""
        action = input_data.get("action")
        name = input_data.get("name")
        description = input_data.get("description")

        data = _load_messages()

        if action == "list":
            channels = list(data.get("channels", {}).keys())
            return ToolResult(success=True, data={
                "channels": channels,
                "count": len(channels)
            })

        if action == "create" and name:
            if name not in data["channels"]:
                data["channels"][name] = []
            if description:
                if "channel_meta" not in data:
                    data["channel_meta"] = {}
                data["channel_meta"][name] = {"description": description, "created_at": datetime.now().isoformat()}
            _save_messages(data)
            return ToolResult(success=True, data={
                "channel": name,
                "status": "created"
            })

        if action == "info" and name:
            messages = data.get("channels", {}).get(name, [])
            meta = data.get("channel_meta", {}).get(name, {})
            return ToolResult(success=True, data={
                "channel": name,
                "message_count": len(messages),
                "meta": meta
            })

        return ToolResult(success=False, error=f"Unknown action: {action}")


class MessageTemplateTool(BaseTool):
    """Manage message templates."""

    name = "message_template"
    description = "Create or use message templates"

    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "list", "use", "get"],
                "description": "Action to perform"
            },
            "name": {
                "type": "string",
                "description": "Template name"
            },
            "template": {
                "type": "string",
                "description": "Template content (for create)"
            },
            "variables": {
                "type": "object",
                "description": "Variables for template (for use)"
            }
        },
        "required": ["action"]
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Manage templates."""
        action = input_data.get("action")
        name = input_data.get("name")
        template = input_data.get("template")
        variables = input_data.get("variables")

        data = _load_messages()

        if "templates" not in data:
            data["templates"] = {}

        if action == "list":
            return ToolResult(success=True, data={
                "templates": list(data["templates"].keys()),
                "count": len(data["templates"])
            })

        if action == "get" and name:
            if name not in data["templates"]:
                return ToolResult(success=False, error=f"Template '{name}' not found")
            return ToolResult(success=True, data={
                "name": name,
                "content": data["templates"][name]["content"],
                "created_at": data["templates"][name].get("created_at")
            })

        if action == "create" and name and template:
            data["templates"][name] = {
                "content": template,
                "created_at": datetime.now().isoformat()
            }
            _save_messages(data)
            return ToolResult(success=True, data={
                "template": name,
                "status": "created"
            })

        if action == "use" and name and variables:
            if name not in data["templates"]:
                return ToolResult(success=False, error=f"Template '{name}' not found")
            content = data["templates"][name]["content"]
            for key, val in variables.items():
                content = content.replace(f"{{{key}}}", str(val))
            return ToolResult(success=True, data={
                "template": name,
                "content": content
            })

        return ToolResult(success=False, error=f"Unknown action: {action}")


# Register tools
tool_registry.register(MessageSendTool())
tool_registry.register(MessageListTool())
tool_registry.register(MessageChannelTool())
tool_registry.register(MessageTemplateTool())
