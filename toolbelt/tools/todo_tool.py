"""TodoWriteTool — persistent todo list management.

Stores todos in ~/.stack-3.0/todos.json

Operations:
  - add    : add a new todo item
  - complete: mark a todo as completed
  - delete : remove a todo by id
  - list   : list all todos (optionally filtered)

Input schema:
  operation : str  — one of add, complete, delete, list
  task      : str  — description of the task (required for add)
  todo_id   : str  — id of the todo (required for complete/delete)
  priority  : str  — low|medium|high|urgent (default: medium, for add)
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .base import BaseTool, ToolResult
from .registry import get_registry

TOOL_NAME = "TodoWrite"
DATA_DIR = os.path.expanduser("~/.stack-3.0")
TODOS_FILE = os.path.join(DATA_DIR, "todos.json")


def _load_todos() -> list[dict[str, Any]]:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(TODOS_FILE):
        try:
            with open(TODOS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_todos(todos: list[dict[str, Any]]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TODOS_FILE, "w") as f:
        json.dump(todos, f, indent=2, default=str)


class TodoWriteTool(BaseTool[dict[str, Any], dict[str, Any]]):
    """Persistent todo list tool supporting add, complete, delete, and list operations."""

    name = TOOL_NAME
    description = "Manage a persistent session todo list: add, complete, delete, or list items."
    search_hint = "manage session todo checklist add complete delete"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "complete", "delete", "list"],
                    "description": "Operation to perform",
                },
                "task": {
                    "type": "string",
                    "description": "Task description (required for 'add' operation)",
                },
                "todo_id": {
                    "type": "string",
                    "description": "Todo ID (required for 'complete' and 'delete' operations)",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "Priority level for 'add' operation (default: medium)",
                    "default": "medium",
                },
            },
            "required": ["operation"],
        }

    def validate_input(self, input_data: dict[str, Any]) -> tuple[bool, str | None]:
        op = input_data.get("operation")
        if op == "add" and not input_data.get("task"):
            return False, "Error: 'task' is required when adding a todo"
        if op in ("complete", "delete") and not input_data.get("todo_id"):
            return False, f"Error: 'todo_id' is required for '{op}' operation"
        return True, None

    def execute(self, input_data: dict[str, Any]) -> ToolResult[dict[str, Any]]:
        op = input_data.get("operation")
        todos = _load_todos()

        if op == "add":
            # Support both 'item' and 'task' for flexibility
            if "item" in input_data and "task" not in input_data:
                input_data["task"] = input_data["item"]
            return self._add(todos, input_data)
        elif op == "complete":
            return self._complete(todos, input_data)
        elif op == "delete":
            return self._delete(todos, input_data)
        elif op == "list":
            return self._list(todos, input_data)
        else:
            return ToolResult(success=False, error=f"Unknown operation: {op}")

    def _add(self, todos: list[dict[str, Any]], input_data: dict[str, Any]) -> ToolResult[dict[str, Any]]:
        todo_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()
        item = {
            "id": todo_id,
            "content": input_data["task"],
            "status": "pending",
            "priority": input_data.get("priority", "medium"),
            "created_at": now,
            "updated_at": now,
        }
        todos.append(item)
        _save_todos(todos)
        return ToolResult(
            success=True,
            data={"id": todo_id, "content": item["content"], "status": "pending", "priority": item["priority"]},
        )

    def _complete(self, todos: list[dict[str, Any]], input_data: dict[str, Any]) -> ToolResult[dict[str, Any]]:
        todo_id = input_data["todo_id"]
        for t in todos:
            if t["id"] == todo_id:
                t["status"] = "completed"
                t["updated_at"] = datetime.now(timezone.utc).isoformat()
                _save_todos(todos)
                return ToolResult(success=True, data={"id": todo_id, "status": "completed"})
        return ToolResult(success=False, error=f"Todo #{todo_id} not found")

    def _delete(self, todos: list[dict[str, Any]], input_data: dict[str, Any]) -> ToolResult[dict[str, Any]]:
        todo_id = input_data["todo_id"]
        original_len = len(todos)
        todos[:] = [t for t in todos if t["id"] != todo_id]
        if len(todos) == original_len:
            return ToolResult(success=False, error=f"Todo #{todo_id} not found")
        _save_todos(todos)
        return ToolResult(success=True, data={"id": todo_id, "deleted": True})

    def _list(self, todos: list[dict[str, Any]], input_data: dict[str, Any]) -> ToolResult[dict[str, Any]]:
        status_filter = input_data.get("status")
        if status_filter:
            todos = [t for t in todos if t.get("status") == status_filter]
        return ToolResult(
            success=True,
            data={
                "todos": todos,
                "total": len(todos),
                "pending": sum(1 for t in _load_todos() if t.get("status") == "pending"),
                "completed": sum(1 for t in _load_todos() if t.get("status") == "completed"),
            },
        )

    def map_result_to_message(self, result: dict, tool_use_id: str | None = None) -> str:
        if "error" in result and not result.get("success", True):
            return result["error"]
        data = result.get("data", {})
        op = data.get("operation", "")
        if op == "add":
            return f"Todo #{data['id']} added: {data['content']} [{data['status']}]"
        elif op == "complete":
            return f"Todo #{data['id']} marked as completed."
        elif op == "delete":
            return f"Todo #{data['id']} deleted."
        elif op == "list":
            items = data.get("todos", [])
            if not items:
                return "No todos found."
            lines = [f"{data['total']} todo(s) (pending: {data['pending']}, completed: {data['completed']}):\n"]
            for t in items:
                lines.append(f"  [{t['status']:9}] #{t['id']} [{t.get('priority','medium'):6}] {t['content']}")
            return "\n".join(lines)
        return str(data)


# Auto-register
get_registry().register(TodoWriteTool())
