"""Hierarchical Tool Router for Stack 3.0 tools."""

from __future__ import annotations

from typing import Any
from .registry import get_registry, ToolRegistry

class ToolRouter:
    """
    Implements a two-stage tool selection process to prevent prompt saturation.
    Includes a 'Fast-Path' to skip hierarchical routing for common simple queries.

    Stage 1: Agent selects a tool category from the list of available categories.
    Stage 2: The framework provides the specific tools available within that category.
    """

    def __init__(self, registry: ToolRegistry | None = None):
        self.registry = registry or get_registry()
        # Fast-path cache: maps simple query patterns to specific tool names
        self._fast_path_cache: dict[str, str] = {
            "time": "get_current_time",
            "date": "get_current_date",
            "weather": "get_weather",
            "help": "show_help",
        }

    def fast_path_route(self, query: str) -> str | None:
        """
        Check if the query matches a known simple pattern to skip hierarchical routing.
        Returns the tool name if found, else None.
        """
        query_lower = query.lower()
        for pattern, tool_name in self._fast_path_cache.items():
            if pattern in query_lower:
                return tool_name
        return None

    def get_categories(self) -> list[str]:

        """Retrieve the list of available tool categories for Stage 1."""
        return self.registry.list_categories()

    def get_tools_for_category(self, category: str) -> dict[str, dict[str, Any]]:
        """Retrieve tools for a specific category for Stage 2."""
        return self.registry.list_tools_in_category(category)

    def route_to_category(self, category_name: str) -> dict[str, dict[str, Any]]:
        """
        Helper method to route to a category and return its tools.
        If the category is not found, it returns an empty dict or a warning.
        """
        return self.get_tools_for_category(category_name)

# Global router instance
tool_router = ToolRouter()
