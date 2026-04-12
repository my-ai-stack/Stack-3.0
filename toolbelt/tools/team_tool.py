"""TeamCreateTool - Multi-agent team coordination for Stack 3.0"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseTool, ToolParam, ToolResult
from .registry import tool_registry

TEAMS_FILE = Path.home() / ".stack-3.0" / "teams.json"


def _load_teams() -> Dict[str, Any]:
    """Load teams from disk."""
    TEAMS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if TEAMS_FILE.exists():
        return json.loads(TEAMS_FILE.read_text())
    return {"teams": []}


def _save_teams(data: Dict[str, Any]) -> None:
    """Save teams to disk."""
    TEAMS_FILE.write_text(json.dumps(data, indent=2))


class TeamCreateTool(BaseTool):
    """Create a team of agents for coordinated work."""

    name = "team_create"
    description = "Create a team of agents that can work together on tasks"

    input_schema = {
        "type": "object",
        "properties": {
            "team_name": {
                "type": "string",
                "description": "Name for the team"
            },
            "agents": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "role": {"type": "string"},
                        "skills": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "description": "List of agents in the team"
            },
            "task": {
                "type": "string",
                "description": "Initial task for the team"
            },
            "coordination_mode": {
                "type": "string",
                "enum": ["parallel", "sequential", "hierarchical"],
                "default": "parallel",
                "description": "How agents coordinate"
            }
        },
        "required": ["team_name", "agents"]
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Create a new team."""
        team_name = input_data.get("team_name")
        agents = input_data.get("agents")
        task = input_data.get("task", "")
        coordination_mode = input_data.get("coordination_mode", "parallel")

        data = _load_teams()

        team_id = str(uuid.uuid4())[:8]
        team = {
            "id": team_id,
            "name": team_name,
            "agents": agents,
            "task": task,
            "coordination_mode": coordination_mode,
            "status": "created",
            "created_at": datetime.now().isoformat(),
            "results": []
        }

        data["teams"].append(team)
        _save_teams(data)

        return ToolResult(success=True, data={
            "team_id": team_id,
            "team_name": team_name,
            "status": "created",
            "agents_count": len(agents) if agents else 0,
            "coordination_mode": coordination_mode,
            "created_at": team["created_at"]
        })


class TeamDisbandTool(BaseTool):
    """Disband a team."""

    name = "team_disband"
    description = "Disband and clean up a team"

    input_schema = {
        "type": "object",
        "properties": {
            "team_id": {
                "type": "string",
                "description": "Team ID to disband"
            }
        },
        "required": ["team_id"]
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Disband team."""
        team_id = input_data.get("team_id")
        data = _load_teams()
        teams = data["teams"]
        original_count = len(teams)
        teams = [t for t in teams if t["id"] != team_id]

        if len(teams) == original_count:
            return ToolResult(success=False, error=f"Team {team_id} not found")

        data["teams"] = teams
        _save_teams(data)

        return ToolResult(success=True, data={
            "team_id": team_id,
            "status": "disbanded"
        })


class TeamListTool(BaseTool):
    """List all teams."""

    name = "team_list"
    description = "List all teams and their status"

    input_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """List teams."""
        data = _load_teams()
        return ToolResult(success=True, data={
            "teams": data.get("teams", []),
            "count": len(data.get("teams", []))
        })


class TeamStatusTool(BaseTool):
    """Get status of a specific team."""

    name = "team_status"
    description = "Get detailed status of a team"

    input_schema = {
        "type": "object",
        "properties": {
            "team_id": {
                "type": "string",
                "description": "Team ID to check"
            }
        },
        "required": ["team_id"]
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Get team status."""
        team_id = input_data.get("team_id")
        data = _load_teams()
        for team in data.get("teams", []):
            if team["id"] == team_id:
                return ToolResult(success=True, data=team)

        return ToolResult(success=False, error=f"Team {team_id} not found")


class TeamAssignTaskTool(BaseTool):
    """Assign a task to a team."""

    name = "team_assign"
    description = "Assign a new task to an existing team"

    input_schema = {
        "type": "object",
        "properties": {
            "team_id": {
                "type": "string",
                "description": "Team ID"
            },
            "task": {
                "type": "string",
                "description": "Task to assign"
            },
            "agent_name": {
                "type": "string",
                "description": "Specific agent to assign to (optional)"
            }
        },
        "required": ["team_id", "task"]
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Assign task to team."""
        team_id = input_data.get("team_id")
        task = input_data.get("task")
        agent_name = input_data.get("agent_name")

        data = _load_teams()
        for team in data.get("teams", []):
            if team["id"] == team_id:
                if agent_name:
                    team["current_task"] = {"task": task, "agent": agent_name, "assigned_at": datetime.now().isoformat()}
                else:
                    team["task"] = task
                    team["current_task"] = {"task": task, "assigned_at": datetime.now().isoformat()}
                _save_teams(data)
                return ToolResult(success=True, data={
                    "team_id": team_id,
                    "task": task,
                    "agent": agent_name,
                    "status": "assigned"
                })

        return ToolResult(success=False, error=f"Team {team_id} not found")


# Register tools
tool_registry.register(TeamCreateTool())
tool_registry.register(TeamDisbandTool())
tool_registry.register(TeamListTool())
tool_registry.register(TeamStatusTool())
tool_registry.register(TeamAssignTaskTool())
