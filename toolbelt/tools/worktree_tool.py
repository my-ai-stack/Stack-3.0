"""WorktreeTool - Git worktree management for Stack 3.0"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .base import BaseTool, ToolResult
from .registry import tool_registry

WORKTREES_FILE = Path.home() / ".stack-3.0" / "worktrees.json"


def _load_worktrees() -> Dict[str, Any]:
    """Load worktree state."""
    WORKTREES_FILE.parent.mkdir(parents=True, exist_ok=True)
    if WORKTREES_FILE.exists():
        return json.loads(WORKTREES_FILE.read_text())
    return {"worktrees": []}


def _save_worktrees(data: Dict[str, Any]) -> None:
    """Save worktree state."""
    WORKTREES_FILE.write_text(json.dumps(data, indent=2))


def _run_git(args: list) -> tuple:
    """Run git command."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1


class EnterWorktreeTool(BaseTool):
    """Enter a git worktree."""

    name = "enter_worktree"
    description = "Enter or create a git worktree"

    input_schema = {
        "type": "object",
        "properties": {
            "worktree_path": {"type": "string", "description": "Path for the worktree"},
            "branch": {"type": "string", "description": "Branch name (optional, will use current if not specified)"},
            "create": {"type": "boolean", "default": False, "description": "Create worktree if it doesn't exist"}
        },
        "required": ["worktree_path"]
    }

    async def execute(self, worktree_path: str, branch: Optional[str] = None, create: bool = False) -> ToolResult:
        """Enter worktree."""
        wt = Path(worktree_path)

        if wt.exists() and create:
            return ToolResult(success=False, error=f"Worktree path exists and create=true: {worktree_path}")

        data = _load_worktrees()

        # Check if worktree already registered
        for existing in data.get("worktrees", []):
            if existing.get("path") == worktree_path:
                return ToolResult(success=True, data={
                    "worktree_id": existing.get("id"),
                    "path": worktree_path,
                    "branch": existing.get("branch"),
                    "status": "already_registered"
                })

        # Create worktree if requested
        if create:
            if not branch:
                # Get current branch
                stdout, _, code = _run_git(["branch", "--show-current"])
                branch = stdout.strip() or "main"

            stdout, stderr, code = _run_git(["worktree", "add", worktree_path, branch])
            if code != 0:
                return ToolResult(success=False, error=f"Failed to create worktree: {stderr}")

        # Register worktree
        wt_id = f"wt_{len(data.get('worktrees', [])) + 1}"
        worktree_entry = {
            "id": wt_id,
            "path": worktree_path,
            "branch": branch,
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }

        data.setdefault("worktrees", []).append(worktree_entry)
        _save_worktrees(data)

        return ToolResult(success=True, data={
            "worktree_id": wt_id,
            "path": worktree_path,
            "branch": branch,
            "status": "entered"
        })


class ExitWorktreeTool(BaseTool):
    """Exit a git worktree."""

    name = "exit_worktree"
    description = "Exit and optionally remove a worktree"

    input_schema = {
        "type": "object",
        "properties": {
            "worktree_id": {"type": "string", "description": "Worktree ID to exit"},
            "cleanup": {"type": "boolean", "default": False, "description": "Remove the worktree directory"}
        },
        "required": ["worktree_id"]
    }

    async def execute(self, worktree_id: str, cleanup: bool = False) -> ToolResult:
        """Exit worktree."""
        data = _load_worktrees()

        worktree = None
        for wt in data.get("worktrees", []):
            if wt.get("id") == worktree_id:
                worktree = wt
                break

        if not worktree:
            return ToolResult(success=False, error=f"Worktree {worktree_id} not found")

        if cleanup:
            stdout, stderr, code = _run_git(["worktree", "remove", worktree["path"]])
            if code != 0:
                return ToolResult(success=False, error=f"Failed to remove worktree: {stderr}")

        # Archive and remove from registry
        archive_dir = Path.home() / ".stack-3.0" / "archives"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_file = archive_dir / f"worktree_{worktree_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        archive_file.write_text(json.dumps(worktree, indent=2))

        data["worktrees"] = [w for w in data["worktrees"] if w.get("id") != worktree_id]
        _save_worktrees(data)

        return ToolResult(success=True, data={
            "worktree_id": worktree_id,
            "path": worktree.get("path"),
            "status": "exited",
            "cleaned_up": cleanup,
            "archived_to": str(archive_file) if cleanup else None
        })


class ListWorktreesTool(BaseTool):
    """List all registered worktrees."""

    name = "list_worktrees"
    description = "List all git worktrees"

    input_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }

    async def execute(self) -> ToolResult:
        """List worktrees."""
        data = _load_worktrees()

        return ToolResult(success=True, data={
            "worktrees": data.get("worktrees", []),
            "count": len(data.get("worktrees", []))
        })


# Register tools
tool_registry.register(EnterWorktreeTool())
tool_registry.register(ExitWorktreeTool())
tool_registry.register(ListWorktreesTool())
