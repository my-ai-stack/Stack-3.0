"""FileReadTool - Read file contents for Stack 3.0"""

import os
from pathlib import Path
from typing import Optional

from .base import BaseTool, ToolResult
from .registry import tool_registry


class FileReadTool(BaseTool):
    """Read contents of a file."""

    name = "file_read"
    description = "Read contents of a file"
    is_noisy = True

    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to read"},
            "offset": {"type": "number", "description": "Line offset to start reading"},
            "limit": {"type": "number", "description": "Maximum lines to read"},
            "show_lines": {"type": "boolean", "default": False, "description": "Include line numbers"}
        },
        "required": ["path"]
    }

    async def execute(self, path: str, offset: Optional[int] = None, limit: Optional[int] = None, show_lines: bool = False) -> ToolResult:
        """Read file."""
        file_path = Path(path)

        if not file_path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")

        if not file_path.is_file():
            return ToolResult(success=False, error=f"Not a file: {path}")

        try:
            lines = file_path.read_text().split('\n')
        except Exception as e:
            return ToolResult(success=False, error=f"Cannot read file: {e}")

        total_lines = len(lines)

        # Apply offset
        if offset is not None and offset > 0:
            lines = lines[offset:]
        elif offset is not None:
            offset = 0

        # Apply limit
        if limit is not None and limit > 0:
            lines = lines[:limit]

        if show_lines:
            start_line = (offset or 0) + 1
            content = '\n'.join(f"{i}: {line}" for i, line in enumerate(lines, start_line))
        else:
            content = '\n'.join(lines)

        return ToolResult(success=True, data={
            "path": path,
            "content": content,
            "lines_read": len(lines),
            "total_lines": total_lines,
            "offset": offset,
            "truncated": limit is not None and len(lines) >= limit
        })


class FileExistsTool(BaseTool):
    """Check if a file exists."""

    name = "file_exists"
    description = "Check if a file or directory exists"

    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to check"}
        },
        "required": ["path"]
    }

    async def execute(self, path: str) -> ToolResult:
        """Check existence."""
        p = Path(path)
        return ToolResult(success=True, data={
            "path": path,
            "exists": p.exists(),
            "is_file": p.is_file() if p.exists() else None,
            "is_dir": p.is_dir() if p.exists() else None
        })


# Register tools
tool_registry.register(FileReadTool())
tool_registry.register(FileExistsTool())
