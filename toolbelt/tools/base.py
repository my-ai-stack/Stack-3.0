"""Base tool class for Stack 3.0 tools."""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, TypeVar


TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


@dataclass
class ToolParam:
    """Definition of a tool parameter."""

    name: str
    description: str
    type: str = "string"
    required: bool = True
    default: Any = None


@dataclass
class ToolResult:
    """Result returned by a tool execution."""

    success: bool = True
    data: Any = None
    error: str | None = None
    duration_seconds: float = 0.0


class BaseTool(ABC, Generic[TInput, TOutput]):
    """Abstract base class for all Stack 3.0 tools.

    Subclasses must implement:
      - name: str — unique identifier
      - description: str — human-readable description
      - input_schema: dict — JSON schema for parameters
      - execute(input: TInput) -> ToolResult[TOutput]

    Optional overrides:
      - validate_input(input: dict) -> tuple[bool, str | None]
      - is_enabled() -> bool
    """

    name: str = ""
    description: str = ""
    category: str = "General"
    is_noisy: bool = False
    search_hint: str = ""
    max_result_size_chars: int = 100_000

    @property
    def input_schema(self) -> dict[str, Any]:
        """JSON schema for tool input parameters."""
        return {}

    @property
    def output_schema(self) -> dict[str, Any]:
        """JSON schema for tool output."""
        return {}

    def is_enabled(self) -> bool:
        """Whether the tool is currently available."""
        return True

    def validate_input(self, input_data: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate input before execution. Returns (valid, error_message)."""
        return True, None

    @abstractmethod
    def execute(self, input_data: TInput) -> ToolResult[TOutput]:
        """Execute the tool with the given input. Must be implemented by subclasses."""
        ...

    async def call(self, input_data: dict[str, Any]) -> ToolResult[TOutput]:
        """High-level call wrapper: validate → execute → timing.

        Handles both sync and async execute methods, and provides
        a hybrid dispatch to support both dictionary and positional arguments.
        """
        valid, error = self.validate_input(input_data)
        if not valid:
            return ToolResult(success=False, error=error or "Validation failed")

        start = time.perf_counter()
        try:
            import inspect
            # Hybrid Dispatcher:
            # 1. Check if the execute method is designed for a single dictionary input
            sig = inspect.signature(self.execute)
            params = list(sig.parameters.values())

            if len(params) == 1 and (params[0].name == 'input_data' or params[0].kind == inspect.Parameter.VAR_KEYWORD):
                # High-Performance Path: Pass dictionary directly
                result = self.execute(input_data)
            else:
                # Compatibility Path: Unpack dictionary into positional/keyword arguments
                result = self.execute(**input_data)

            # Handle async execute methods
            if asyncio.iscoroutine(result):
                result = await result

            result.duration_seconds = time.perf_counter() - start
            return result
        except Exception as exc:
            return ToolResult(
                success=False,
                error=str(exc),
                duration_seconds=time.perf_counter() - start,
            )

    def map_result_to_message(self, result: TOutput, tool_use_id: str | None = None) -> str:
        """Format a successful result for display."""
        return str(result)
