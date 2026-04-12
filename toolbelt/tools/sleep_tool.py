"""SleepTool - Simple delay tool for Stack 3.0"""

import asyncio
import time
from datetime import datetime

from .base import BaseTool, ToolResult
from .registry import tool_registry


class SleepTool(BaseTool):
    """Pause execution for a specified duration."""

    name = "sleep"
    description = "Pause execution for a specified number of seconds"

    input_schema = {
        "type": "object",
        "properties": {
            "seconds": {"type": "number", "description": "Number of seconds to sleep"}
        },
        "required": ["seconds"]
    }

    async def execute(self, seconds: float) -> ToolResult:
        """Sleep."""
        if seconds <= 0:
            return ToolResult(success=False, error="Seconds must be positive")

        if seconds > 3600:
            return ToolResult(success=False, error="Maximum sleep is 3600 seconds (1 hour)")

        start = time.time()
        await asyncio.sleep(seconds)
        elapsed = time.time() - start

        return ToolResult(success=True, data={
            "requested_seconds": seconds,
            "actual_elapsed": elapsed,
            "completed_at": datetime.now().isoformat()
        })


class WaitForTool(BaseTool):
    """Wait for a condition to become true."""

    name = "wait_for"
    description = "Wait for a condition with timeout"

    input_schema = {
        "type": "object",
        "properties": {
            "seconds": {"type": "number", "description": "Maximum seconds to wait"},
            "poll_interval": {"type": "number", "default": 1.0, "description": "Seconds between checks"}
        },
        "required": ["seconds"]
    }

    async def execute(self, seconds: float, poll_interval: float = 1.0) -> ToolResult:
        """Wait with polling."""
        if seconds <= 0 or poll_interval <= 0:
            return ToolResult(success=False, error="All values must be positive")

        start = time.time()
        elapsed = 0

        while elapsed < seconds:
            await asyncio.sleep(min(poll_interval, seconds - elapsed))
            elapsed = time.time() - start

        return ToolResult(success=True, data={
            "waited_seconds": seconds,
            "actual_elapsed": elapsed,
            "timed_out": True
        })


# Register tools
tool_registry.register(SleepTool())
tool_registry.register(WaitForTool())
