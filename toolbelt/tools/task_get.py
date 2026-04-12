"""TaskGetTool - Get details of a specific task for Stack 3.0"""

import json
from pathlib import Path

from .base import BaseTool, ToolResult
from .registry import tool_registry

TASKS_FILE = Path.home() / ".stack-3.0" / "tasks.json"


def _load_tasks() -> dict:
    """Load tasks from disk."""
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if TASKS_FILE.exists():
        return json.loads(TASKS_FILE.read_text())
    return {"tasks": []}


class TaskGetTool(BaseTool):
    """Get details of a specific task."""

    name = "task_get"
    description = "Get details of a task by ID"

    input_schema = {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "Task ID"}
        },
        "required": ["task_id"]
    }

    async def execute(self, task_id: str) -> ToolResult:
        """Get task details."""
        data = _load_tasks()

        for task in data.get("tasks", []):
            if task.get("id") == task_id:
                return ToolResult(success=True, data={
                    "task": task,
                    "found": True
                })

        return ToolResult(success=False, error=f"Task {task_id} not found")


class TaskOutputTool(BaseTool):
    """Get output from a completed task."""

    name = "task_output"
    description = "Get output from a completed task"

    input_schema = {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "Task ID"}
        },
        "required": ["task_id"]
    }

    async def execute(self, task_id: str) -> ToolResult:
        """Get task output."""
        data = _load_tasks()

        for task in data.get("tasks", []):
            if task.get("id") == task_id:
                output = task.get("output") or task.get("result")
                status = task.get("status", "unknown")

                return ToolResult(success=True, data={
                    "task_id": task_id,
                    "status": status,
                    "output": output,
                    "has_output": output is not None
                })

        return ToolResult(success=False, error=f"Task {task_id} not found")


class TaskStopTool(BaseTool):
    """Stop a running task."""

    name = "task_stop"
    description = "Stop a running or pending task"

    input_schema = {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "Task ID to stop"}
        },
        "required": ["task_id"]
    }

    async def execute(self, task_id: str) -> ToolResult:
        """Stop task."""
        data = _load_tasks()

        for task in data.get("tasks", []):
            if task.get("id") == task_id:
                old_status = task.get("status")
                task["status"] = "stopped"
                task["stopped_at"] = datetime.now().isoformat()

                TASKS_FILE.write_text(json.dumps(data, indent=2))

                return ToolResult(success=True, data={
                    "task_id": task_id,
                    "old_status": old_status,
                    "new_status": "stopped"
                })

        return ToolResult(success=False, error=f"Task {task_id} not found")


from datetime import datetime
