"""TaskManagementTool — create, list, update, and delete tasks.

Tasks are stored in ~/.stack-3.0/tasks.json.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

from .base import BaseTool, ToolResult
from .registry import get_registry

TOOL_NAME = "TaskManagement"
DATA_DIR = os.path.expanduser("~/.stack-3.0")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")


def _load_tasks() -> list[dict[str, Any]]:
    """Load tasks from disk."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_tasks(tasks: list[dict[str, Any]]) -> None:
    """Persist tasks to disk."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2, default=str)


# ── sub-commands as separate tool classes ─────────────────────────────────────


class TaskCreateTool(BaseTool[dict[str, Any], dict[str, Any]]):
    """Create a new task.

    Parameters
    ----------
    subject : str
        Brief, actionable title (required).
    description : str
        Detailed description of what needs to be done.
    status : str, optional
        One of "pending" (default), "in_progress", "completed", "cancelled".
    priority : str, optional
        One of "low", "medium", "high", "urgent" (default "medium").
    tags : list[str], optional
        Arbitrary labels for the task.
    metadata : dict, optional
        Arbitrary extra data to attach.
    """

    name = "TaskCreate"
    description = "Create a new task in the task list."
    search_hint = "create a task in the task list"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Brief title for the task"},
                "description": {"type": "string", "description": "What needs to be done"},
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed", "cancelled"],
                    "description": "Task status (default: pending)",
                    "default": "pending",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "Priority level (default: medium)",
                    "default": "medium",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Labels to attach to the task",
                },
                "metadata": {
                    "type": "object",
                    "description": "Arbitrary extra data",
                },
            },
            "required": ["subject"],
        }

    def validate_input(self, input_data: dict[str, Any]) -> tuple[bool, str | None]:
        if not input_data.get("subject"):
            return False, "Error: subject is required"
        return True, None

    def execute(self, input_data: dict[str, Any]) -> ToolResult[dict[str, Any]]:
        tasks = _load_tasks()
        task_id = str(uuid.uuid4())[:8]

        task = {
            "id": task_id,
            "subject": input_data["subject"],
            "description": input_data.get("description", ""),
            "status": input_data.get("status", "pending"),
            "priority": input_data.get("priority", "medium"),
            "tags": input_data.get("tags", []),
            "metadata": input_data.get("metadata", {}),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        tasks.append(task)
        _save_tasks(tasks)

        return ToolResult(
            success=True,
            data={"id": task_id, "subject": task["subject"], "status": task["status"]},
        )

    def map_result_to_message(self, result: dict, tool_use_id: str | None = None) -> str:
        return f"Task #{result['id']} created: {result['subject']} [{result['status']}]"


class TaskListTool(BaseTool[dict[str, Any], dict[str, Any]]):
    """List tasks, optionally filtered by status.

    Parameters
    ----------
    status : str, optional
        Filter by status: "pending", "in_progress", "completed", "cancelled".
    tag : str, optional
        Filter by tag.
    limit : int, optional
        Maximum number of tasks to return (default 50).
    """

    name = "TaskList"
    description = "List tasks from the task list, optionally filtered."
    search_hint = "list tasks in the task list"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed", "cancelled"],
                    "description": "Filter by status",
                },
                "tag": {"type": "string", "description": "Filter by tag"},
                "limit": {
                    "type": "integer",
                    "description": "Maximum tasks to return (default 50)",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 200,
                },
            },
            "properties": {
                "status": {"type": "string"},
                "tag": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
        }

    def execute(self, input_data: dict[str, Any]) -> ToolResult[dict[str, Any]]:
        tasks = _load_tasks()
        status_filter = input_data.get("status")
        tag_filter = input_data.get("tag")
        limit = input_data.get("limit", 50)

        if status_filter:
            tasks = [t for t in tasks if t.get("status") == status_filter]
        if tag_filter:
            tasks = [t for t in tasks if tag_filter in t.get("tags", [])]

        tasks = tasks[:limit]

        return ToolResult(
            success=True,
            data={
                "tasks": [
                    {
                        "id": t["id"],
                        "subject": t["subject"],
                        "status": t["status"],
                        "priority": t.get("priority", "medium"),
                        "tags": t.get("tags", []),
                        "created_at": t.get("created_at", ""),
                    }
                    for t in tasks
                ],
                "total": len(tasks),
            },
        )

    def map_result_to_message(self, result: dict, tool_use_id: str | None = None) -> str:
        tasks = result.get("tasks", [])
        if not tasks:
            return "No tasks found."

        lines = [f"{result['total']} task(s):\n"]
        for t in tasks:
            tags = ", ".join(t.get("tags", [])) if t.get("tags") else ""
            lines.append(f"  [{t['status']:12}] #{t['id']} {t['subject']} {'| ' + tags if tags else ''}")
        return "\n".join(lines)


class TaskUpdateTool(BaseTool[dict[str, Any], dict[str, Any]]):
    """Update a task by ID.

    Parameters
    ----------
    id : str
        The task ID (required).
    subject : str, optional
        New title.
    description : str, optional
        New description.
    status : str, optional
        New status.
    priority : str, optional
        New priority.
    tags : list[str], optional
        New tags (replaces existing).
    """

    name = "TaskUpdate"
    description = "Update an existing task by ID."
    search_hint = "update a task in the task list"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Task ID (required)"},
                "subject": {"type": "string", "description": "New title"},
                "description": {"type": "string", "description": "New description"},
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed", "cancelled"],
                },
                "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Replace tags"},
                "metadata": {"type": "object", "description": "Merge into metadata"},
            },
            "required": ["id"],
        }

    def validate_input(self, input_data: dict[str, Any]) -> tuple[bool, str | None]:
        if not input_data.get("id"):
            return False, "Error: id is required"
        return True, None

    def execute(self, input_data: dict[str, Any]) -> ToolResult[dict[str, Any]]:
        tasks = _load_tasks()
        task_id = input_data["id"]

        found = False
        for t in tasks:
            if t["id"] == task_id:
                if "subject" in input_data:
                    t["subject"] = input_data["subject"]
                if "description" in input_data:
                    t["description"] = input_data["description"]
                if "status" in input_data:
                    t["status"] = input_data["status"]
                if "priority" in input_data:
                    t["priority"] = input_data["priority"]
                if "tags" in input_data:
                    t["tags"] = input_data["tags"]
                if "metadata" in input_data:
                    t["metadata"] = {**t.get("metadata", {}), **input_data["metadata"]}
                t["updated_at"] = datetime.now(timezone.utc).isoformat()
                found = True
                break

        if not found:
            return ToolResult(success=False, error=f"Task #{task_id} not found")

        _save_tasks(tasks)
        return ToolResult(success=True, data={"id": task_id, "status": t.get("status")})

    def map_result_to_message(self, result: dict, tool_use_id: str | None = None) -> str:
        return f"Task #{result['id']} updated."


class TaskDeleteTool(BaseTool[dict[str, Any], dict[str, Any]]):
    """Delete a task by ID.

    Parameters
    ----------
    id : str
        The task ID to delete (required).
    """

    name = "TaskDelete"
    description = "Delete a task by ID."
    search_hint = "delete a task"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Task ID to delete"},
            },
            "required": ["id"],
        }

    def validate_input(self, input_data: dict[str, Any]) -> tuple[bool, str | None]:
        if not input_data.get("id"):
            return False, "Error: id is required"
        return True, None

    def execute(self, input_data: dict[str, Any]) -> ToolResult[dict[str, Any]]:
        tasks = _load_tasks()
        task_id = input_data["id"]
        original_len = len(tasks)
        tasks = [t for t in tasks if t["id"] != task_id]

        if len(tasks) == original_len:
            return ToolResult(success=False, error=f"Task #{task_id} not found")

        _save_tasks(tasks)
        return ToolResult(success=True, data={"id": task_id, "deleted": True})

    def map_result_to_message(self, result: dict, tool_use_id: str | None = None) -> str:
        return f"Task #{result['id']} deleted."


# Register all task tools
_registry = get_registry()
_registry.register(TaskCreateTool())
_registry.register(TaskListTool())
_registry.register(TaskUpdateTool())
_registry.register(TaskDeleteTool())
