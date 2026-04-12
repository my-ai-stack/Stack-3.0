"""FileWriteTool - Write content to files for Stack 3.0"""

import os
from datetime import datetime
from pathlib import Path

from .base import BaseTool, ToolResult
from .registry import tool_registry

BACKUP_DIR = Path.home() / ".stack-3.0" / "backups"


class FileWriteTool(BaseTool):
    """Write content to a file."""

    name = "file_write"
    description = "Write content to a file"

    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to write"},
            "content": {"type": "string", "description": "Content to write"},
            "append": {"type": "boolean", "default": False, "description": "Append instead of overwrite"},
            "create_backup": {"type": "boolean", "default": True, "description": "Create backup if file exists"}
        },
        "required": ["path", "content"]
    }

    async def execute(self, path: str, content: str, append: bool = False, create_backup: bool = True) -> ToolResult:
        """Write file."""
        file_path = Path(path)

        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        backup_path = None

        # Backup existing file
        if file_path.exists() and create_backup and not append:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.name}.{timestamp}.bak"
            backup_path = BACKUP_DIR / backup_name
            backup_path.write_text(file_path.read_text())

        # Write content
        try:
            if append:
                existing = file_path.read_text() if file_path.exists() else ""
                file_path.write_text(existing + content)
            else:
                file_path.write_text(content)
        except Exception as e:
            return ToolResult(success=False, error=f"Cannot write file: {e}")

        return ToolResult(success=True, data={
            "path": str(file_path),
            "bytes_written": len(content),
            "backup": str(backup_path) if backup_path else None,
            "mode": "append" if append else "overwrite"
        })


class FileDeleteTool(BaseTool):
    """Delete a file."""

    name = "file_delete"
    description = "Delete a file"

    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to delete"},
            "create_backup": {"type": "boolean", "default": True},
            "force": {"type": "boolean", "default": False, "description": "Force deletion if file is read-only"}
        },
        "required": ["path"]
    }

    async def execute(self, path: str, create_backup: bool = True, force: bool = False) -> ToolResult:
        """Delete file."""
        file_path = Path(path)

        if not file_path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")

        if not file_path.is_file():
            return ToolResult(success=False, error=f"Not a file: {path}")

        backup_path = None

        # Backup before delete
        if create_backup:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.name}.{timestamp}.deleted.bak"
            backup_path = BACKUP_DIR / backup_name
            backup_path.write_text(file_path.read_text())

        try:
            file_path.unlink()
        except Exception as e:
            return ToolResult(success=False, error=f"Cannot delete file: {e}")

        return ToolResult(success=True, data={
            "path": str(file_path),
            "deleted": True,
            "backup": str(backup_path) if backup_path else None
        })


# Register tools
tool_registry.register(FileWriteTool())
tool_registry.register(FileDeleteTool())
