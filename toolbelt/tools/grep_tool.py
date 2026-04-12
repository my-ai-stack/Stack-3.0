"""GrepTool - Enhanced code search for Stack 3.0"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseTool, ToolResult
from .registry import tool_registry


class GrepTool(BaseTool):
    """Search files using regex patterns."""

    name = "grep"
    description = "Search for regex patterns in files"
    is_noisy = True

    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern to search"},
            "path": {"type": "string", "description": "Directory or file path to search"},
            "recursive": {"type": "boolean", "default": True, "description": "Search recursively"},
            "case_sensitive": {"type": "boolean", "default": True},
            "context_lines": {"type": "number", "default": 0, "description": "Lines of context before/after"},
            "file_pattern": {"type": "string", "description": "Filter by file pattern (e.g., *.py, *.js)"},
            "max_results": {"type": "number", "default": 1000, "description": "Maximum matches to return"}
        },
        "required": ["pattern", "path"]
    }

    def execute(self, input_data: dict) -> ToolResult:
        """Search for pattern in files."""
        pattern = input_data.get('pattern')
        path = input_data.get('path')
        recursive = input_data.get('recursive', True)
        case_sensitive = input_data.get('case_sensitive', True)
        context_lines = input_data.get('context_lines', 0)
        file_pattern = input_data.get('file_pattern')
        max_results = input_data.get('max_results', 1000)
        search_path = Path(path)
        if not search_path.exists():
            return ToolResult(success=False, error=f"Path not found: {path}")

        try:
            regex = re.compile(pattern, 0 if case_sensitive else re.IGNORECASE)
        except re.error as e:
            return ToolResult(success=False, error=f"Invalid regex: {e}")

        matches = []
        visited_dirs = set()

        def matches_pattern(text: str) -> List[str]:
            """Find all matches in text with line numbers."""
            results = []
            for i, line in enumerate(text.split('\n'), 1):
                if regex.search(line):
                    results.append((i, line.rstrip()))
            return results

        def search_file(file_path: Path):
            """Search a single file."""
            if file_pattern:
                if not any(file_path.match(p) for p in file_pattern.split(',')):
                    return

            try:
                content = file_path.read_text(errors='ignore')
            except Exception:
                return

            for line_num, line_text in matches_pattern(content):
                match_entry = {
                    "file": str(file_path),
                    "line": line_num,
                    "text": line_text
                }

                if context_lines > 0:
                    lines = content.split('\n')
                    start = max(0, line_num - context_lines - 1)
                    end = min(len(lines), line_num + context_lines)
                    match_entry["context"] = {
                        "before": lines[start:line_num - 1],
                        "after": lines[line_num:end]
                    }

                matches.append(match_entry)

                if len(matches) >= max_results:
                    return True  # Stop searching
            return False

        def walk_dir(dir_path: Path):
            """Walk directory tree."""
            if str(dir_path) in visited_dirs:
                return
            visited_dirs.add(str(dir_path))

            try:
                for item in dir_path.iterdir():
                    # Skip hidden and common ignore directories
                    if item.name.startswith('.') or item.name in ('__pycache__', 'node_modules', '.git', 'venv', 'env'):
                        continue

                    if item.is_file():
                        if search_file(item):
                            return True
                    elif item.is_dir() and recursive:
                        if walk_dir(item):
                            return True
            except PermissionError:
                pass
            return False

        walk_dir(search_path)

        return ToolResult(success=True, data={
            "pattern": pattern,
            "path": str(path),
            "matches": matches,
            "count": len(matches),
            "truncated": len(matches) >= max_results
        })


class GrepCountTool(BaseTool):
    """Count occurrences of pattern in files."""

    name = "grep_count"
    description = "Count occurrences of pattern in files"

    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern"},
            "path": {"type": "string", "description": "Directory or file path"},
            "recursive": {"type": "boolean", "default": True},
            "case_sensitive": {"type": "boolean", "default": True},
            "file_pattern": {"type": "string", "description": "Filter by file pattern"}
        },
        "required": ["pattern", "path"]
    }

    def execute(self, input_data: dict) -> ToolResult:
        """Count pattern matches."""
        grep_result = GrepTool().execute(input_data)

        counts = {}
        for match in grep_result.data.get("matches", []):
            file_path = match["file"]
            counts[file_path] = counts.get(file_path, 0) + 1

        return ToolResult(success=True, data={
            "pattern": input_data.get('pattern'),
            "total_matches": len(grep_result.data.get("matches", [])),
            "by_file": counts
        })


# Register tools
tool_registry.register(GrepTool())
tool_registry.register(GrepCountTool())
