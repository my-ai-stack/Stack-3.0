"""GlobTool - File pattern matching for Stack 3.0"""

import fnmatch
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseTool, ToolResult
from .registry import tool_registry

# Default exclusions
DEFAULT_EXCLUDES = {
    '.git', '.svn', '.hg', '__pycache__', 'node_modules', '.venv', 'venv',
    'env', '.idea', '.vscode', '.DS_Store', '*.pyc', '*.pyo', '*.so',
    '*.dylib', '.cache', '.pytest_cache', '.mypy_cache', 'dist', 'build',
    '*.egg-info', '.tox', '.nox'
}


def _should_exclude(path: Path, exclude_patterns: List[str]) -> bool:
    """Check if path should be excluded."""
    name = path.name

    # Check default exclusions
    if name in DEFAULT_EXCLUDES:
        return True

    # Check custom patterns
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(str(path), pattern):
            return True

    return False


def _glob_pattern_to_regex(pattern: str) -> str:
    """Convert glob pattern to regex."""
    # Handle ** for recursive matching
    regex_parts = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == '*':
            if i + 1 < len(pattern) and pattern[i + 1] == '*':
                # ** matches everything including /
                regex_parts.append('.*')
                i += 2
            else:
                # * matches everything except /
                regex_parts.append('[^/]*')
                i += 1
        elif c == '?':
            regex_parts.append('.')
            i += 1
        elif c == '[':
            # Character class
            j = i + 1
            if j < len(pattern) and pattern[j] == '!':
                regex_parts.append('[^')
                j += 1
            else:
                regex_parts.append('[')
            while j < len(pattern) and pattern[j] != ']':
                regex_parts.append(re.escape(pattern[j]))
                j += 1
            regex_parts.append(']')
            i = j + 1
        else:
            regex_parts.append(re.escape(c))
            i += 1

    return ''.join(regex_parts)


def _match_glob(path: Path, pattern: str) -> bool:
    """Check if path matches glob pattern."""
    import re

    # Normalize pattern - handle **/*.py style patterns
    if pattern.startswith('**/'):
        # Recursive pattern
        regex_pattern = _glob_pattern_to_regex(pattern)
        regex = re.compile(regex_pattern)
        return bool(regex.match(str(path))) or bool(regex.match(path.name))
    elif '**' in pattern:
        regex_pattern = _glob_pattern_to_regex(pattern)
        regex = re.compile(regex_pattern)
        return bool(regex.match(str(path)))
    else:
        # Simple pattern
        return fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(str(path), pattern)


class GlobTool(BaseTool):
    """Find files matching glob patterns."""

    name = "glob"
    description = "Find files matching glob patterns"
    is_noisy = True

    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Glob pattern (e.g., **/*.py, *.js)"},
            "path": {"type": "string", "description": "Base directory to search"},
            "exclude": {"type": "array", "items": {"type": "string"}, "description": "Patterns to exclude"},
            "max_results": {"type": "number", "default": 1000, "description": "Maximum results"},
            "files_only": {"type": "boolean", "default": True, "description": "Only return files"}
        },
        "required": ["pattern"]
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Find files matching pattern."""
        pattern = input_data.get("pattern")
        if not pattern:
            return ToolResult(success=False, error="Missing required parameter: pattern")

        path = input_data.get("path")
        exclude = input_data.get("exclude")
        max_results = input_data.get("max_results", 1000)
        files_only = input_data.get("files_only", True)

        if path:
            search_path = Path(path)
        else:
            search_path = Path.cwd()

        if not search_path.exists():
            return ToolResult(success=False, error=f"Path not found: {search_path}")

        exclude_patterns = exclude or []
        matches = []
        visited_dirs = set()

        def search_dir(dir_path: Path, depth: int = 0):
            """Recursively search directory."""
            if str(dir_path) in visited_dirs:
                return
            visited_dirs.add(str(dir_path))

            try:
                for item in dir_path.iterdir():
                    if _should_exclude(item, exclude_patterns):
                        continue

                    if item.is_file():
                        if _match_glob(item, pattern):
                            matches.append(str(item))
                            if len(matches) >= max_results:
                                return True
                    elif item.is_dir():
                        # Handle ** pattern
                        if '**' in pattern:
                            search_dir(item, depth + 1)
                        elif depth < 20:  # Limit depth for non-** patterns
                            search_dir(item, depth + 1)
            except PermissionError:
                pass

            return False

        search_dir(search_path)

        return ToolResult(success=True, data={
            "pattern": pattern,
            "base_path": str(search_path),
            "matches": matches,
            "count": len(matches),
            "truncated": len(matches) >= max_results
        })


class GlobListTool(BaseTool):
    """List all files in directory with optional filtering."""

    name = "glob_list"
    description = "List files in directory with optional pattern filter"

    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path"},
            "pattern": {"type": "string", "description": "Optional pattern filter"},
            "recursive": {"type": "boolean", "default": False, "description": "Recursive listing"},
            "max_results": {"type": "number", "default": 500}
        },
        "required": ["path"]
    }

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """List directory contents."""
        path = input_data.get("path")
        if not path:
            return ToolResult(success=False, error="Missing required parameter: path")

        pattern = input_data.get("pattern")
        recursive = input_data.get("recursive", False)
        max_results = input_data.get("max_results", 500)

        dir_path = Path(path)
        if not dir_path.exists():
            return ToolResult(success=False, error=f"Path not found: {path}")

        matches = []

        def search_dir(d: Path, depth: int = 0):
            if len(matches) >= max_results:
                return

            try:
                for item in d.iterdir():
                    if item.name.startswith('.'):
                        continue

                    if pattern:
                        if _match_glob(item, pattern):
                            matches.append(str(item))
                    else:
                        matches.append(str(item))

                    if item.is_dir() and recursive and depth < 10:
                        search_dir(item, depth + 1)

                    if len(matches) >= max_results:
                        return
            except PermissionError:
                pass

        search_dir(dir_path)

        return ToolResult(success=True, data={
            "path": str(dir_path),
            "files": matches,
            "count": len(matches)
        })


# Register tools
tool_registry.register(GlobTool())
tool_registry.register(GlobListTool())
