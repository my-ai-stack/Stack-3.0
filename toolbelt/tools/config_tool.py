"""ConfigTool — runtime configuration management for Stack 3.0.

Stores configuration in ~/.stack-3.0/config.json

Operations:
  - get    : retrieve a configuration value
  - set    : set a configuration value
  - list   : list all configuration keys and values
  - delete : remove a configuration key

Input schema:
  operation : str — one of get, set, list, delete
  key       : str — configuration key (required for get/set/delete)
  value     : any — new value (required for set)
"""

from __future__ import annotations

import json
import os
from typing import Any

from .base import BaseTool, ToolResult
from .registry import get_registry

TOOL_NAME = "Config"
DATA_DIR = os.path.expanduser("~/.stack-3.0")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")


def _load_config() -> dict[str, Any]:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config(config: dict[str, Any]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, default=str)


# Supported configuration keys and their metadata
SUPPORTED_KEYS: dict[str, dict[str, Any]] = {
    "theme": {
        "type": "string",
        "options": ["light", "dark", "system"],
        "default": "system",
        "description": "UI theme",
    },
    "model": {
        "type": "string",
        "description": "Default model to use",
        "default": "",
    },
    "max_tokens": {
        "type": "number",
        "description": "Maximum tokens per response",
        "default": 4096,
    },
    "temperature": {
        "type": "number",
        "description": "Sampling temperature",
        "default": 0.7,
    },
    "verbose": {
        "type": "boolean",
        "description": "Enable verbose output",
        "default": False,
    },
    "permissions.defaultMode": {
        "type": "string",
        "options": ["auto", "plan", "bypass"],
        "description": "Default permissions mode",
        "default": "auto",
    },
    "tools.enabled": {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of enabled tool names",
        "default": [],
    },
    "tools.disabled": {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of disabled tool names",
        "default": [],
    },
}


class ConfigTool(BaseTool[dict[str, Any], dict[str, Any]]):
    """Runtime configuration management tool.

    Supports get, set, list, and delete operations on the persistent config store.
    """

    name = TOOL_NAME
    description = "Get, set, list, or delete Stack 3.0 runtime configuration settings."
    search_hint = "get or set configuration settings theme model permissions"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["get", "set", "list", "delete"],
                    "description": "Configuration operation",
                },
                "key": {
                    "type": "string",
                    "description": "Configuration key (required for get/set/delete)",
                },
                "value": {
                    "description": "New value (required for 'set' operation)",
                },
            },
            "required": ["operation"],
        }

    def validate_input(self, input_data: dict[str, Any]) -> tuple[bool, str | None]:
        op = input_data.get("operation")
        if op in ("get", "set", "delete") and not input_data.get("key"):
            return False, f"Error: 'key' is required for '{op}' operation"
        if op == "set" and "value" not in input_data:
            return False, "Error: 'value' is required for 'set' operation"
        return True, None

    def execute(self, input_data: dict[str, Any]) -> ToolResult[dict[str, Any]]:
        op = input_data.get("operation")
        key = input_data.get("key")
        value = input_data.get("value")

        if op == "get":
            return self._get(key)
        elif op == "set":
            return self._set(key, value)
        elif op == "list":
            return self._list()
        elif op == "delete":
            return self._delete(key)
        else:
            return ToolResult(success=False, error=f"Unknown operation: {op}")

    def _get(self, key: str | None) -> ToolResult[dict[str, Any]]:
        if key is None:
            return ToolResult(success=False, error="Key is required for 'get'")
        config = _load_config()
        current = config.get(key)
        meta = SUPPORTED_KEYS.get(key, {})
        return ToolResult(
            success=True,
            data={
                "operation": "get",
                "key": key,
                "value": current if current is not None else meta.get("default"),
                "default": meta.get("default"),
            },
        )

    def _set(self, key: str | None, value: Any) -> ToolResult[dict[str, Any]]:
        if key is None:
            return ToolResult(success=False, error="Key is required for 'set'")

        meta = SUPPORTED_KEYS.get(key)
        if meta is not None:
            expected_type = meta.get("type")
            # Type coercion
            if expected_type == "boolean":
                if isinstance(value, str):
                    value = value.lower() in ("true", "1", "yes")
            elif expected_type == "number":
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    return ToolResult(
                        success=False,
                        error=f"Invalid number value for '{key}': {value}",
                    )
            # Validate options
            options = meta.get("options")
            if options and value not in options:
                return ToolResult(
                    success=False,
                    error=f"Invalid value '{value}' for '{key}'. Options: {', '.join(options)}",
                )

        config = _load_config()
        previous = config.get(key)
        config[key] = value
        _save_config(config)

        return ToolResult(
            success=True,
            data={
                "operation": "set",
                "key": key,
                "previousValue": previous,
                "newValue": value,
            },
        )

    def _list(self) -> ToolResult[dict[str, Any]]:
        config = _load_config()
        meta = SUPPORTED_KEYS

        items = []
        all_keys = sorted(set(list(config.keys()) + list(meta.keys())))
        for k in all_keys:
            items.append({
                "key": k,
                "value": config.get(k, meta.get(k, {}).get("default")),
                "description": meta.get(k, {}).get("description", ""),
                "type": meta.get(k, {}).get("type", "unknown"),
                "options": meta.get(k, {}).get("options"),
                "is_default": k not in config,
            })

        return ToolResult(
            success=True,
            data={
                "operation": "list",
                "settings": items,
                "total": len(items),
            },
        )

    def _delete(self, key: str | None) -> ToolResult[dict[str, Any]]:
        if key is None:
            return ToolResult(success=False, error="Key is required for 'delete'")
        config = _load_config()
        if key not in config:
            return ToolResult(success=False, error=f"Key '{key}' not found in config")
        previous = config.pop(key)
        _save_config(config)
        return ToolResult(
            success=True,
            data={
                "operation": "delete",
                "key": key,
                "previousValue": previous,
            },
        )

    def map_result_to_message(self, result: dict, tool_use_id: str | None = None) -> str:
        if not result.get("success", True):
            return f"Error: {result.get('error')}"
        data = result.get("data", {})
        op = data.get("operation", "")

        if op == "get":
            val = data.get("value")
            default = data.get("default")
            note = f" (default: {default})" if default is not None and val == default else ""
            return f"{data['key']} = {json.dumps(val)}{note}"

        elif op == "set":
            return f"Set {data['key']} = {json.dumps(data['newValue'])}"

        elif op == "list":
            settings = data.get("settings", [])
            if not settings:
                return "No configuration settings found."
            lines = [f"{data['total']} setting(s):\n"]
            for s in settings:
                val = json.dumps(s["value"])
                note = f" [{s['type']}]" if s["type"] != "unknown" else ""
                if s["is_default"]:
                    note += " (default)"
                lines.append(f"  {s['key']:30} = {val}{note}")
            return "\n".join(lines)

        elif op == "delete":
            return f"Deleted {data['key']} (was: {json.dumps(data['previousValue'])})"

        return str(data)


# Auto-register
get_registry().register(ConfigTool())
