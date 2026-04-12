"""FileEditTool - Intelligent file editing for Stack 3.0"""

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseTool, ToolResult
from .registry import tool_registry

# Protected paths that should not be edited
PROTECTED_PATHS = {
    '/etc', '/usr', '/bin', '/sbin', '/lib', '/System',
    'C:\\Windows', 'C:\\Program Files', 'C:\\Program Files (x86)',
    '/System', '/Library', '/Applications'
}

BACKUP_DIR = Path.home() / ".stack-3.0" / "backups"


def _is_protected_path(path: str) -> bool:
    """Check if path is protected."""
    abs_path = str(Path(path).resolve())
    for protected in PROTECTED_PATHS:
        if abs_path.startswith(protected):
            return True
    return False


def _create_backup(content: str, file_path: str) -> str:
    """Create backup of file content."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{Path(file_path).name}.{timestamp}.bak"
    backup_path = BACKUP_DIR / backup_name
    backup_path.write_text(content)
    return str(backup_path)


class FileEditInsertTool(BaseTool):
    """Insert content at specific line or after a pattern."""

    name = "file_edit_insert"
    description = "Insert content at a specific line number or after a pattern"

    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to edit"},
            "content": {"type": "string", "description": "Content to insert"},
            "line": {"type": "number", "description": "Line number to insert at (1-indexed)"},
            "after_pattern": {"type": "string", "description": "Or insert after this regex pattern"},
            "create_backup": {"type": "boolean", "default": True}
        },
        "required": ["path", "content"]
    }

    async def execute(self, path: str, content: str, line: Optional[int] = None, after_pattern: Optional[str] = None, create_backup: bool = True) -> ToolResult:
        """Insert content into file."""
        if _is_protected_path(path):
            return ToolResult(success=False, error="Cannot edit protected path")

        if not Path(path).exists():
            return ToolResult(success=False, error=f"File not found: {path}")

        original_content = Path(path).read_text()
        lines = original_content.split('\n')

        if after_pattern:
            pattern = re.compile(after_pattern)
            for i, l in enumerate(lines):
                if pattern.search(l):
                    lines.insert(i + 1, content)
                    break
            else:
                return ToolResult(success=False, error=f"Pattern not found: {after_pattern}")
        elif line:
            if line < 1 or line > len(lines) + 1:
                return ToolResult(success=False, error=f"Line {line} out of range (1-{len(lines) + 1})")
            lines.insert(line - 1, content)
        else:
            return ToolResult(success=False, error="Must specify line or after_pattern")

        if create_backup:
            backup_path = _create_backup(original_content, path)

        new_content = '\n'.join(lines)
        Path(path).write_text(new_content)

        return ToolResult(success=True, data={
            "path": path,
            "operation": "insert",
            "line": line or "after_pattern",
            "backup": backup_path if create_backup else None
        })


class FileEditDeleteTool(BaseTool):
    """Delete lines from a file."""

    name = "file_edit_delete"
    description = "Delete lines from a file"

    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path"},
            "line": {"type": "number", "description": "Single line to delete (1-indexed)"},
            "line_start": {"type": "number", "description": "Start line (1-indexed)"},
            "line_end": {"type": "number", "description": "End line (1-indexed, inclusive)"},
            "pattern": {"type": "string", "description": "Or delete lines matching this regex"},
            "create_backup": {"type": "boolean", "default": True}
        },
        "required": ["path"]
    }

    async def execute(self, path: str, line: Optional[int] = None, line_start: Optional[int] = None, line_end: Optional[int] = None, pattern: Optional[str] = None, create_backup: bool = True) -> ToolResult:
        """Delete lines from file."""
        if _is_protected_path(path):
            return ToolResult(success=False, error="Cannot edit protected path")

        if not Path(path).exists():
            return ToolResult(success=False, error=f"File not found: {path}")

        original_content = Path(path).read_text()
        lines = original_content.split('\n')

        if pattern:
            regex = re.compile(pattern)
            deleted = [i for i, l in enumerate(lines) if regex.search(l)]
            lines = [l for i, l in enumerate(lines) if i not in deleted]
            deleted_count = len(deleted)
        elif line:
            if line < 1 or line > len(lines):
                return ToolResult(success=False, error=f"Line {line} out of range (1-{len(lines)})")
            del lines[line - 1]
            deleted_count = 1
        else:
            if line_start is None or line_end is None:
                return ToolResult(success=False, error="Must specify line, line_start/line_end or pattern")

            if line_start < 1 or line_end > len(lines) or line_start > line_end:
                return ToolResult(success=False, error=f"Invalid line range ({line_start}-{line_end})")

            deleted_count = line_end - line_start + 1
            lines = lines[:line_start - 1] + lines[line_end:]

        if create_backup:
            backup_path = _create_backup(original_content, path)

        new_content = '\n'.join(lines)
        Path(path).write_text(new_content)

        return ToolResult(success=True, data={
            "path": path,
            "operation": "delete",
            "lines_deleted": deleted_count,
            "backup": backup_path if create_backup else None
        })


class FileEditReplaceTool(BaseTool):
    """Replace content using regex."""

    name = "file_edit_replace"
    description = "Replace content using regex pattern"

    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path"},
            "pattern": {"type": "string", "description": "Regex pattern to find"},
            "replacement": {"type": "string", "description": "Replacement text"},
            "replace_all": {"type": "boolean", "default": False, "description": "Replace all occurrences"},
            "case_sensitive": {"type": "boolean", "default": True},
            "create_backup": {"type": "boolean", "default": True}
        },
        "required": ["path", "pattern", "replacement"]
    }

    async def execute(self, path: str, pattern: str, replacement: str, replace_all: bool = False, case_sensitive: bool = True, create_backup: bool = True) -> ToolResult:
        """Replace content in file."""
        if _is_protected_path(path):
            return ToolResult(success=False, error="Cannot edit protected path")

        if not Path(path).exists():
            return ToolResult(success=False, error=f"File not found: {path}")

        original_content = Path(path).read_text()

        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(pattern, flags)

        if replace_all:
            new_content, count = regex.subn(replacement, original_content)
        else:
            match = regex.search(original_content)
            if not match:
                return ToolResult(success=False, error=f"Pattern not found: {pattern}")
            new_content = original_content[:match.start()] + replacement + original_content[match.end():]
            count = 1

        if create_backup:
            backup_path = _create_backup(original_content, path)

        Path(path).write_text(new_content)

        return ToolResult(success=True, data={
            "path": path,
            "operation": "replace",
            "replacements": count,
            "backup": backup_path if create_backup else None
        })


class FileEditTool(BaseTool):
    """Main file editing tool with multiple operations."""

    name = "file_edit"
    description = "Edit files with insert, delete, replace operations"

    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path"},
            "operation": {
                "type": "string",
                "enum": ["insert", "delete", "replace"],
                "description": "Operation type"
            },
            "content": {"type": "string", "description": "Content for insert/replace"},
            "line_start": {"type": "number", "description": "Start line for delete"},
            "line_end": {"type": "number", "description": "End line for delete"},
            "pattern": {"type": "string", "description": "Regex pattern"},
            "replacement": {"type": "string", "description": "Replacement text"},
            "replace_all": {"type": "boolean", "default": False},
            "create_backup": {"type": "boolean", "default": True}
        },
        "required": ["path", "operation"]
    }

    async def execute(self, path: str, operation: str, content: Optional[str] = None, line_start: Optional[int] = None, line_end: Optional[int] = None, pattern: Optional[str] = None, replacement: Optional[str] = None, replace_all: bool = False, create_backup: bool = True) -> ToolResult:
        """Execute file edit operation."""
        if operation == "insert" and content:
            return await FileEditInsertTool().execute(path, content, line=line_start, after_pattern=pattern, create_backup=create_backup)
        elif operation == "delete":
            return await FileEditDeleteTool().execute(path, line_start=line_start, line_end=line_end, pattern=pattern, create_backup=create_backup)
        elif operation == "replace" and pattern and replacement:
            return await FileEditReplaceTool().execute(path, pattern, replacement, replace_all=replace_all, create_backup=create_backup)
        else:
            return ToolResult(success=False, error=f"Invalid operation or missing parameters: {operation}")


# Register tools
tool_registry.register(FileEditInsertTool())
tool_registry.register(FileEditDeleteTool())
tool_registry.register(FileEditReplaceTool())
tool_registry.register(FileEditTool())
