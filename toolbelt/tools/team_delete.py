"""TeamDeleteTool - Delete/disband a team for Stack 3.0"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .base import BaseTool, ToolResult
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


class TeamDeleteTool(BaseTool):
    """Delete or disband a team."""

    name = "team_delete"
    description = "Delete and disband a team"

    input_schema = {
        "type": "object",
        "properties": {
            "team_id": {"type": "string", "description": "Team ID to delete"},
            "force": {"type": "boolean", "default": False, "description": "Force delete even if tasks pending"}
        },
        "required": ["team_id"]
    }

    async def execute(self, team_id: str, force: bool = False) -> ToolResult:
        """Delete team."""
        data = _load_teams()

        # Find team
        team = None
        for t in data.get("teams", []):
            if t.get("id") == team_id:
                team = t
                break

        if not team:
            return ToolResult(success=False, error=f"Team {team_id} not found")

        # Check for pending tasks
        if not force and team.get("status") == "active":
            pending_tasks = [a for a in team.get("agents", []) if a.get("status") == "active"]
            if pending_tasks:
                return ToolResult(success=False, error=f"Team has {len(pending_tasks)} active agents. Use force=true to delete anyway.")

        # Archive team before deletion
        archive_dir = Path.home() / ".stack-3.0" / "archives"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_file = archive_dir / f"team_{team_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        archive_file.write_text(json.dumps(team, indent=2))

        # Remove from teams list
        data["teams"] = [t for t in data["teams"] if t.get("id") != team_id]
        _save_teams(data)

        return ToolResult(success=True, data={
            "team_id": team_id,
            "team_name": team.get("name"),
            "status": "deleted",
            "archived_to": str(archive_file)
        })


class TeamLeaveTool(BaseTool):
    """Leave a team (for agents)."""

    name = "team_leave"
    description = "Leave a team"

    input_schema = {
        "type": "object",
        "properties": {
            "team_id": {"type": "string", "description": "Team ID"},
            "agent_name": {"type": "string", "description": "Agent name to remove"}
        },
        "required": ["team_id", "agent_name"]
    }

    async def execute(self, team_id: str, agent_name: str) -> ToolResult:
        """Leave team."""
        data = _load_teams()

        for team in data.get("teams", []):
            if team.get("id") == team_id:
                agents = team.get("agents", [])
                original_count = len(agents)
                agents = [a for a in agents if a.get("name") != agent_name]

                if len(agents) == original_count:
                    return ToolResult(success=False, error=f"Agent {agent_name} not found in team")

                team["agents"] = agents
                _save_teams(data)

                return ToolResult(success=True, data={
                    "team_id": team_id,
                    "agent_removed": agent_name,
                    "status": "removed"
                })

        return ToolResult(success=False, error=f"Team {team_id} not found")


# Register tools
tool_registry.register(TeamDeleteTool())
tool_registry.register(TeamLeaveTool())
