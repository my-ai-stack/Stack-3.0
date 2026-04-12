"""BriefTool - Generate briefings for Stack 3.0"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseTool, ToolResult
from .registry import tool_registry


class BriefTool(BaseTool):
    """Generate a briefing for a task."""

    name = "brief"
    description = "Generate a structured briefing for a task"

    input_schema = {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "Main task or goal"},
            "context": {"type": "string", "description": "Additional context"},
            "constraints": {"type": "array", "items": {"type": "string"}, "description": "Constraints or requirements"},
            "hints": {"type": "array", "items": {"type": "string"}, "description": " Helpful hints"},
            "format": {"type": "string", "enum": ["concise", "detailed"], "default": "concise"}
        },
        "required": ["task"]
    }

    async def execute(self, task: str, context: Optional[str] = None, constraints: Optional[List[str]] = None, hints: Optional[List[str]] = None, format: str = "concise") -> ToolResult:
        """Generate brief."""
        brief_id = f"brief_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        sections = {
            "id": brief_id,
            "task": task,
            "created_at": datetime.now().isoformat()
        }

        if context:
            sections["context"] = context

        if constraints:
            sections["constraints"] = constraints

        if hints:
            sections["hints"] = hints

        if format == "detailed":
            sections["format_version"] = "detailed"
            sections["priority"] = "medium"
            sections["estimated_complexity"] = "unknown"
        else:
            sections["format_version"] = "concise"

        return ToolResult(success=True, data=sections)


class BriefSummaryTool(BaseTool):
    """Summarize a previous brief or conversation."""

    name = "brief_summary"
    description = "Generate a summary briefing"

    input_schema = {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Content to summarize"},
            "max_points": {"type": "number", "default": 5, "description": "Maximum key points"}
        },
        "required": ["content"]
    }

    async def execute(self, content: str, max_points: int = 5) -> ToolResult:
        """Generate summary."""
        # Simple extractive summarization
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        points = lines[:max_points]

        return ToolResult(success=True, data={
            "summary": points,
            "total_lines": len(lines),
            "points_extracted": len(points)
        })


# Register tools
tool_registry.register(BriefTool())
tool_registry.register(BriefSummaryTool())
