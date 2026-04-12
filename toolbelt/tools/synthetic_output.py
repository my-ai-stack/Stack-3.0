"""SyntheticOutputTool - Generate structured synthetic output for Stack 3.0"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseTool, ToolResult
from .registry import tool_registry


class SyntheticOutputTool(BaseTool):
    """Generate structured synthetic output."""

    name = "synthetic_output"
    description = "Generate structured synthetic output in various formats"

    input_schema = {
        "type": "object",
        "properties": {
            "output_type": {
                "type": "string",
                "enum": ["json", "markdown", "text", "html"],
                "description": "Output format"
            },
            "content": {"type": "string", "description": "Content to format"},
            "metadata": {"type": "object", "description": "Optional metadata"}
        },
        "required": ["output_type", "content"]
    }

    async def execute(self, output_type: str, content: str, metadata: Optional[Dict] = None) -> ToolResult:
        """Generate output."""
        result = {
            "type": output_type,
            "content": content,
            "generated_at": datetime.now().isoformat()
        }

        if metadata:
            result["metadata"] = metadata

        if output_type == "json":
            formatted = json.dumps(result, indent=2)
        elif output_type == "markdown":
            formatted = self._to_markdown(result)
        elif output_type == "html":
            formatted = self._to_html(result)
        else:
            formatted = content

        return ToolResult(success=True, data={
            "type": output_type,
            "formatted": formatted,
            "raw": result
        })

    def _to_markdown(self, data: Dict) -> str:
        """Convert to markdown."""
        lines = [f"# Synthetic Output", f"**Type:** {data.get('type')}", f"**Generated:** {data.get('generated_at')}", ""]

        if data.get("metadata"):
            lines.append("## Metadata")
            for k, v in data["metadata"].items():
                lines.append(f"- **{k}:** {v}")
            lines.append("")

        lines.append("## Content")
        lines.append(data.get("content", ""))
        return '\n'.join(lines)

    def _to_html(self, data: Dict) -> str:
        """Convert to HTML."""
        meta = ""
        if data.get("metadata"):
            meta = "<ul>" + "".join(f"<li><strong>{k}:</strong> {v}</li>" for k, v in data["metadata"].items()) + "</ul>"

        return f"""
<div class="synthetic-output">
  <h2>Synthetic Output</h2>
  <p><strong>Type:</strong> {data.get('type')}</p>
  <p><strong>Generated:</strong> {data.get('generated_at')}</p>
  {meta}
  <div class="content">
    <pre>{data.get('content', '')}</pre>
  </div>
</div>
"""


class StructuredDataTool(BaseTool):
    """Convert unstructured data to structured format."""

    name = "structure_data"
    description = "Convert unstructured data to structured format"

    input_schema = {
        "type": "object",
        "properties": {
            "data": {"type": "string", "description": "Data to structure"},
            "schema": {"type": "object", "description": "Target schema"},
            "format": {"type": "string", "enum": ["json", "csv"], "default": "json"}
        },
        "required": ["data"]
    }

    async def execute(self, data: str, schema: Optional[Dict] = None, format: str = "json") -> ToolResult:
        """Structure data."""
        # Simple JSON detection
        try:
            parsed = json.loads(data)
            return ToolResult(success=True, data={
                "parsed": parsed,
                "format": "json",
                "structured": True
            })
        except json.JSONDecodeError:
            pass

        # Treat as plain text
        return ToolResult(success=True, data={
            "data": data,
            "format": "text",
            "structured": False,
            "note": "Could not auto-structure, returned as text"
        })


# Register tools
tool_registry.register(SyntheticOutputTool())
tool_registry.register(StructuredDataTool())
